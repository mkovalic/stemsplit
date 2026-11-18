# How to make a vocal separation engine for music

A **stem** is a separate audio track containing one part of a song, such as vocals, drums, or bass.

In this tutorial, we’ll build a vocal separation engine that takes a song and splits it into two stems:

- **Vocals:** the isolated vocal track.
- **Instrumental:** the accompanying music with the vocals removed.

We’ll use [Demucs](https://github.com/adefossez/demucs), an open-source model for music source separation, and [Modal](https://modal.com/docs/guide) for serverless cloud processing. Modal manages the GPU infrastructure and scales it on demand, with compute billed by the second. A local Python script will upload the song, call the model, and save both stems as WAV files on your computer.

We’ll start with a single song, then submit several songs in parallel. Finally, we’ll use a small sample’s usage costs to estimate the cost of one million similar separations.

## Set up Modal

Start by creating a [Modal account](https://modal.com/). You’ll also need Python 3.11–3.15 installed locally and a [valid payment method](https://modal.com/docs/guide/gpu) on your Modal account to use a GPU.

Create a project folder and activate a virtual environment. On macOS or Linux:

```bash
mkdir -p stemsplit
cd stemsplit
python3 -m venv .venv
source .venv/bin/activate
```

Install the latest Modal client:

```bash
python -m pip install --upgrade modal
```

Then authenticate your computer with your Modal account:

```bash
python -m modal setup
```

Follow the authentication prompts, then check that the client is available:

```bash
python -m modal --version
```

Using `python -m` for both installation and execution keeps these commands tied to the same Python environment.

Create a file named `demucs_demo.py` in the project folder and place an audio file alongside it. For this tutorial, we’ll call the audio file `song.mp3`:

```text
stemsplit/
├── .venv/
├── demucs_demo.py
└── song.mp3
```

## Build the environment

Modal runs our separation function inside a container image. We’ll define that image in Python, specifying the runtime, audio tools, and model dependencies.

Add the following to `demucs_demo.py`. The imports include the standard-library tools we’ll use in the functions below:

```python
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import modal

app = modal.App("stemsplit-demo")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "torch==2.8.0",
        index_url="https://download.pytorch.org/whl/cu126",
    )
    .pip_install(
        "demucs==4.1.0",
        "numpy==2.2.6",
    )
    .run_commands(
        "python -c \"from demucs.pretrained import get_model; "
        "get_model('htdemucs')\""
    )
)
```

The `App` groups the functions that make up our vocal separation engine. The `image` defines the environment those functions will use.

We start with a minimal Debian image running Python 3.11, then install:

- **FFmpeg** to decode audio files.
- **PyTorch** with CUDA 12.6 support to run the model on a GPU.
- **Demucs** to perform music source separation.
- **NumPy** for the numerical operations Demucs depends on.

The final command downloads the `htdemucs` model weights during image construction, making them available to containers started from this image. Each separation will still load the model into memory when it runs.

Modal builds the image when we first run the app and [reuses cached layers](https://modal.com/docs/guide/images#image-caching-and-rebuilds) on subsequent runs. Changing a layer causes that layer and the layers after it to rebuild.

## Run separation on a GPU

The separation function will receive a song as bytes, run Demucs on a GPU, and return the two WAV files.

Add this function below the image definition:

```python
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
```

The `@app.function` decorator tells Modal to run this function using our image. We request an L4 GPU, with a T4 as a fallback. Modal tries the [GPU types in the order listed](https://modal.com/docs/guide/gpu#gpu-fallbacks), based on availability.

Each container gets two CPU cores and 8 GiB of system memory, with a 15-minute execution timeout. For this single-song demo, we cap the function at one container and allow it to scale to zero when idle, using a five-second scale-down window.

Inside the function, we write the uploaded bytes to a temporary file and launch Demucs. The command selects `htdemucs`, requests vocals and accompaniment with `--two-stems vocals`, and uses CUDA for GPU processing. Setting `check=True` makes a failed Demucs command raise an error.

Finally, we read `vocals.wav` and `no_vocals.wav` into memory and return their contents. The temporary directory is cleaned up automatically when the function exits.

## Upload a song and save the stems

The local entrypoint connects your audio file to the GPU function. It reads the song, calls `separate.remote()`, and saves the returned stems on your computer.

Add this entrypoint below `separate`:

```python
@app.local_entrypoint()
def main(file: str):
    source = Path(file).expanduser()
    if not source.is_file():
        raise ValueError(
            f"Expected an existing audio file: {source.resolve()}. "
            "Check the path passed to --file."
        )

    audio = source.read_bytes()
    print(f"Uploading {source.name}...")

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
```

The `@app.local_entrypoint()` decorator makes `main` the starting point for our script. Modal turns the `file` argument into a [`--file` command-line option](https://modal.com/docs/guide/apps#entrypoints-for-ephemeral-apps).

From the project folder, with your virtual environment active, run:

```bash
python -m modal run demucs_demo.py --file "song.mp3"
```

On the first run, Modal builds the image before processing the song. You’ll see build logs, separation progress, and the paths to the saved files.

Once the command finishes, your output folder will contain:

```text
stems/
└── song/
    ├── vocals.wav
    └── no_vocals.wav
```

For a different input filename, the script creates a matching folder under `stems`. Open the two WAV files to listen to the isolated vocals and instrumental.

The [temporary Modal app stops automatically](https://modal.com/docs/guide/apps#ephemeral-apps) when the entrypoint finishes.

## Run multiple songs in parallel

To process a folder of songs, change `max_containers` to `4` in the `separate` function’s decorator. Then **replace** the local entrypoint with:

```python
@app.local_entrypoint()
def main(directory: str = "."):
    sources = sorted(
        path for path in Path(directory).expanduser().iterdir()
        if path.is_file() and path.suffix.lower() in {".mp3", ".opus"}
    )
    if not sources:
        raise ValueError("No MP3 or OPUS files found.")

    audio_files = (source.read_bytes() for source in sources)
    results = separate.map(audio_files, order_outputs=True)

    for source, stems in zip(sources, results):
        output = Path("stems") / source.stem
        output.mkdir(parents=True, exist_ok=True)

        for name, data in stems.items():
            target = output / name
            target.write_bytes(data)
            print(f"Saved: {target.resolve()}")
```

Run it against the folder containing your songs:

```bash
python -m modal run demucs_demo.py --directory "."
```

[`separate.map()`](https://modal.com/docs/guide/scale#parallel-execution-of-inputs) submits the songs for parallel processing and returns results in input order. Each song’s stems are saved in its own folder.

Modal can scale up to four GPU containers with this configuration, subject to availability and workspace limits. You can adjust `max_containers` to control how many workers the function may use.

## Estimate cost and performance at scale

Parallel processing increases throughput by letting separate workers handle different songs simultaneously. Batch completion time also depends on GPU availability, container startup, and file transfers.

Costs accumulate across the active containers. To estimate a larger workload, divide a small batch’s reported usage cost by its number of completed songs, then multiply by your target volume. Use [usage costs before credits and allowances](https://modal.com/docs/guide/billing#generating-billing-reports).

Our twelve-call T4 sample averaged approximately **$0.008 per song**, including compute and output transfers. At that rate:

| Songs processed | Estimated total cost |
| ---: | ---: |
| 10,000 | $80 |
| 100,000 | $800 |
| 1,000,000 | $8,000 |

These estimates assume similar three-to-four-minute songs, T4 GPUs, and two WAV outputs per song. They extrapolate from a small sample and exclude credits, allowances, retained storage, retries, and additional application services. Using an L4 through the fallback configuration will change the cost and performance profile.

For comparison, we estimate **$11,500–$14,400 per million similar songs on [Google Cloud Run with an L4 GPU](https://cloud.google.com/run/pricing)**, including compute and downloads, versus **about $8,000 on Modal**.

For sustained traffic, model loading is a useful optimization target. The current implementation starts a new Demucs process for every song. Moving to its Python API inside a Modal class lets you load the model once with [`@modal.enter()`](https://modal.com/docs/guide/lifecycle-functions) and reuse it across calls in the same container.

You can also increase [`scaledown_window`](https://modal.com/docs/guide/scale#configuring-autoscaling-behavior) to encourage container reuse between requests. Keeping containers idle longer trades additional compute cost for fewer cold starts.

To turn the engine into an application, add an upload endpoint and store the finished stems in object storage so users can retrieve them through download links.
