"""Measure this demo on four audio files, three times each.

Run with: python -m modal run benchmark_demucs.py

This experiment requests T4 with L4 fallback and keeps a container available for
up to 60 seconds between inputs. A reused container still starts a new Demucs process
and loads the model for every call. Timings are not exact billed GPU durations.
"""

import asyncio
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import modal

from demucs_demo import image as demo_image


app = modal.App("stemsplit-benchmark")
image = demo_image.add_local_python_source("demucs_demo")

CSV_FIELDS = [
    "status", "round", "track_index", "source_name", "source_path", "suffix",
    "source_sha256", "input_bytes", "audio_duration_seconds", "format_name",
    "audio_codec", "client_start_utc", "client_end_utc", "client_seconds",
    "subprocess_seconds", "handler_seconds", "handler_start_utc", "handler_end_utc",
    "worker_id", "call_id",
    "container_observation", "gpu_name", "output_bytes", "total_output_bytes",
    "stems_directory", "error_type", "error",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.function(
    image=image,
    gpu=["T4", "L4"],
    cpu=2,
    memory=8192,
    timeout=900,
    min_containers=0,
    max_containers=4,
    scaledown_window=60,
)
def benchmark_separate(audio: bytes, suffix: str) -> dict:
    handler_started = time.perf_counter()
    handler_start_utc = utc_now()
    if suffix not in {".mp3", ".opus"}:
        raise ValueError(f"Unsupported input suffix: {suffix}")

    worker_id = os.environ["MODAL_TASK_ID"]
    call_id = modal.current_function_call_id()
    gpu_name = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        text=True,
    ).strip()

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / f"song{suffix}"
        source.write_bytes(audio)

        subprocess_started = time.perf_counter()
        subprocess.run(
            [
                sys.executable, "-m", "demucs",
                "-n", "htdemucs",
                "--two-stems", "vocals",
                "-d", "cuda",
                "-o", str(root / "output"),
                str(source),
            ],
            check=True,
        )
        subprocess_seconds = time.perf_counter() - subprocess_started

        stems_directory = root / "output" / "htdemucs" / "song"
        stems = {
            name: (stems_directory / name).read_bytes()
            for name in ("vocals.wav", "no_vocals.wav")
        }
        handler_seconds = time.perf_counter() - handler_started

    return {
        "stems": stems,
        "metadata": {
            "worker_id": worker_id,
            "call_id": call_id,
            "gpu_name": gpu_name,
            "subprocess_seconds": subprocess_seconds,
            "handler_seconds": handler_seconds,
            "handler_start_utc": handler_start_utc,
            "handler_end_utc": utc_now(),
            "output_bytes": {name: len(data) for name, data in stems.items()},
        },
    }


def inspect_audio(source: Path, ffprobe: str) -> tuple[dict, bytes]:
    """Complete input inspection outside every client timing interval."""
    inspected = subprocess.run(
        [
            ffprobe, "-v", "error",
            "-show_entries",
            "format=duration,format_name:stream=index,codec_type,codec_name,duration",
            "-of", "json", str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    probe = json.loads(inspected.stdout)
    audio_streams = [
        stream for stream in probe.get("streams", [])
        if stream.get("codec_type") == "audio"
    ]
    if not audio_streams:
        raise ValueError(f"No audio stream found in {source}")

    audio_format = probe.get("format", {})
    duration = None
    for value in [audio_format.get("duration"), audio_streams[0].get("duration")]:
        try:
            candidate = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(candidate) and candidate > 0:
            duration = candidate
            break
    if duration is None:
        raise ValueError(f"Could not determine a positive duration for {source}")

    audio = source.read_bytes()
    return {
        "source_name": source.name,
        "source_path": str(source),
        "suffix": source.suffix.lower(),
        "source_sha256": hashlib.sha256(audio).hexdigest(),
        "input_bytes": len(audio),
        "audio_duration_seconds": duration,
        "format_name": audio_format.get("format_name"),
        "audio_codec": audio_streams[0].get("codec_name"),
    }, audio


def append_result(directory: Path, row: dict) -> None:
    """Persist each result independently; never keep the only copy in memory."""
    with (directory / "runs.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

    csv_path = directory / "runs.csv"
    has_header = csv_path.exists() and csv_path.stat().st_size > 0
    csv_row = {key: row.get(key) for key in CSV_FIELDS}
    if isinstance(csv_row.get("output_bytes"), dict):
        csv_row["output_bytes"] = json.dumps(csv_row["output_bytes"], sort_keys=True)
    with csv_path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        if not has_header:
            writer.writeheader()
        writer.writerow(csv_row)
        stream.flush()
        os.fsync(stream.fileno())


@app.local_entrypoint()
async def main(
    directory: str = ".",
    repeats: int = 3,
    expected_files: int = 4,
    output_root: str = "benchmark-results",
):
    if repeats < 1 or expected_files < 1:
        raise ValueError("repeats and expected_files must both be positive")
    source_directory = Path(directory).expanduser().resolve()
    if not source_directory.is_dir():
        raise ValueError(f"Expected an existing directory: {source_directory}")
    sources = sorted(
        (
            path for path in source_directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".mp3", ".opus"}
        ),
        key=lambda path: path.name.casefold(),
    )
    if len(sources) != expected_files:
        raise ValueError(
            f"Expected {expected_files} MP3/OPUS files in {source_directory}; "
            f"found {len(sources)}: {[source.name for source in sources]}"
        )
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe must be available locally for audio preflight")

    inputs = [inspect_audio(source, ffprobe) for source in sources]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    results_directory = Path(output_root).expanduser().resolve() / timestamp
    results_directory.mkdir(parents=True, exist_ok=False)
    script_directory = Path(__file__).resolve().parent
    config = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "app_id": app.app_id,
        "dashboard_url": await app.get_dashboard_url.aio() if app.app_id else None,
        "repeats": repeats,
        "expected_files": expected_files,
        "execution_order": "three rounds by default; all four tracks concurrently per round",
        "gpu_requested": ["T4", "L4"],
        "cpu_requested_cores": 2,
        "memory_requested_mib": 8192,
        "timeout_seconds": 900,
        "min_containers": 0,
        "max_containers": 4,
        "scaledown_window_seconds": 60,
        "model": "htdemucs",
        "two_stems": "vocals",
        "local_python": sys.version,
        "modal_version": version("modal"),
        "ffprobe": ffprobe,
        "source_files": [metadata for metadata, _audio in inputs],
        "script_sha256": {
            name: hashlib.sha256((script_directory / name).read_bytes()).hexdigest()
            for name in ("benchmark_demucs.py", "demucs_demo.py")
        },
        "measurement_notes": {
            "client_seconds": (
                "Time around .remote.aio(): includes upload, queue/startup, handler, "
                "and response download; excludes input preflight, image building, "
                "and saving local stems."
            ),
            "subprocess_seconds": (
                "Demucs process lifetime, including Python/model loading, decoding, "
                "separation, and output encoding."
            ),
            "handler_seconds": (
                "Handler entry through reading output bytes; includes GPU-name lookup "
                "and input writing; excludes startup before handler entry, temporary "
                "file cleanup, response serialization/transfer, and container cooldown."
            ),
            "container_observation": (
                "first_seen_container or reused_container within this experiment; "
                "every call still launches a new Demucs process and loads the model."
            ),
            "cost": "These timings are not exact billable durations or invoice totals.",
            "output_bytes": "WAV payload bytes, not exact metered network egress.",
            "batch_wall_seconds": "Time for all calls in a round, including dispatch, transfers, and local result saving.",
        },
    }
    (results_directory / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Preflight passed for {len(inputs)} files. Results: {results_directory}")
    print("T4 with L4 fallback; four calls in parallel per round; 60-second scale-down window.")

    async def measure_call(round_number, track_index, source_metadata, audio):
        row = {
            **source_metadata,
            "round": round_number,
            "track_index": track_index,
            "client_start_utc": utc_now(),
        }
        started = time.perf_counter()
        try:
            result = await benchmark_separate.remote.aio(audio, source_metadata["suffix"])
            row["client_seconds"] = time.perf_counter() - started
            row["client_end_utc"] = utc_now()
            row.update(result["metadata"])
            row["status"] = "success"
            return row, result["stems"]
        except Exception as error:
            row.update({
                "client_seconds": time.perf_counter() - started,
                "client_end_utc": utc_now(),
                "status": "failure",
                "error_type": type(error).__name__,
                "error": str(error),
            })
            return row, None

    seen_workers = set()
    for round_number in range(1, repeats + 1):
        batch_started = time.perf_counter()
        batch_start_utc = utc_now()
        print(f"Starting parallel batch {round_number}/{repeats}: {len(inputs)} calls")
        tasks = [
            asyncio.create_task(measure_call(round_number, index, metadata, audio))
            for index, (metadata, audio) in enumerate(inputs, start=1)
        ]
        failures = []
        for completed in asyncio.as_completed(tasks):
            row, stems = await completed
            if row["status"] == "failure":
                append_result(results_directory, row)
                failures.append(row)
                print(f"Failed: {row['source_name']}: {row['error']}")
                continue

            worker_id = row["worker_id"]
            row["container_observation"] = (
                "reused_container" if worker_id in seen_workers else "first_seen_container"
            )
            seen_workers.add(worker_id)
            row["total_output_bytes"] = sum(len(data) for data in stems.values())
            output_directory = None
            if round_number == 1:
                output_directory = (
                    results_directory / "stems"
                    / f"{row['track_index']:02d}-{Path(row['source_name']).stem}"
                )
            row["stems_directory"] = str(output_directory) if output_directory else None
            append_result(results_directory, row)
            if output_directory is not None:
                output_directory.mkdir(parents=True, exist_ok=False)
                for name in ("vocals.wav", "no_vocals.wav"):
                    (output_directory / name).write_bytes(stems[name])
            print(
                f"Round {round_number}/{repeats}, track {row['track_index']}/{len(inputs)}: "
                f"{row['source_name']} | client {row['client_seconds']:.2f}s | "
                f"Demucs process {row['subprocess_seconds']:.2f}s | "
                f"{row['gpu_name']} | {row['container_observation']}"
            )

        batch = {
            "round": round_number,
            "batch_start_utc": batch_start_utc,
            "batch_end_utc": utc_now(),
            "batch_wall_seconds": time.perf_counter() - batch_started,
            "calls": len(tasks),
            "failures": len(failures),
        }
        with (results_directory / "batches.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(batch) + "\n")
        print(f"Batch {round_number}: {batch['batch_wall_seconds']:.2f}s total")
        if failures:
            raise RuntimeError(
                f"Batch {round_number} had {len(failures)} failed calls; "
                f"results saved in {results_directory}"
            )

    print(f"Completed {len(inputs) * repeats} runs. Results: {results_directory}")
