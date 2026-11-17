from pathlib import Path
import subprocess
import sys
import tempfile
import time

import modal

app = modal.App("stemsplit-demo")

# Prepare the cloud environment and download the model weights during the build.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "torch==2.8.0",
        index_url="https://download.pytorch.org/whl/cu126",
    )
    .pip_install("demucs==4.1.0", "numpy==2.2.6")
    .run_commands(
        "python -c \"from demucs.pretrained import get_model; "
        "get_model('htdemucs')\""
    )
)


@app.function(
    image=image,
    gpu=["L4", "T4"],
    cpu=2,
    memory=8192,
    timeout=900,
    min_containers=0,
    max_containers=1,
    scaledown_window=5,
)
def separate(audio: bytes) -> dict[str, bytes]:
    # This function runs on a Modal GPU.
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "song.mp3"
        source.write_bytes(audio)

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

        stems = root / "output" / "htdemucs" / "song"
        return {
            name: (stems / name).read_bytes()
            for name in ("vocals.wav", "no_vocals.wav")
        }


@app.local_entrypoint()
def main(file: str):
    # This entrypoint runs locally.
    source = Path(file).expanduser()
    if not source.is_file():
        raise ValueError(
            f"Expected an existing audio file: {source.resolve()}. "
            "Check the path passed to --file."
        )

    audio = source.read_bytes()
    print(f"Uploading {source.name}...")
    # Includes transfer, queue/startup, and processing; excludes image building.
    started = time.perf_counter()
    results = separate.remote(audio)
    elapsed = time.perf_counter() - started
    print(f"Upload-to-download time: {elapsed:.2f} seconds")

    output = Path("stems") / source.stem
    output.mkdir(parents=True, exist_ok=True)

    for name, data in results.items():
        target = output / name
        target.write_bytes(data)
        print(f"Saved: {target.resolve()}")
