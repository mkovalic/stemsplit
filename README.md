# Stemsplit

Separate music into **vocals** and **instrumental** stems with [Demucs](https://github.com/adefossez/demucs) on [Modal](https://modal.com/docs/guide). Modal provides serverless cloud GPUs, automatic scaling, and per-second compute billing.

## Quickstart

Requires Python 3.11–3.15 and a Modal account with a payment method for GPU access. From the repository folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m modal setup
python -m modal run demucs_demo.py --file "song.mp3"
```

Supply your own audio file. The script saves `vocals.wav` and `no_vocals.wav` under `stems/<song-name>/`. FFmpeg, PyTorch, NumPy, and Demucs are installed in the cloud image.

## Parallel processing and cost

The [batch walkthrough](docs/how-to-make-a-vocal-separation-engine-for-music.md#run-multiple-songs-in-parallel) shows how to process a folder using `separate.map()` and up to four GPU workers.

Our twelve-call T4 sample averaged approximately **$0.008 per song**, including compute and output transfers:

| Songs | Estimated cost |
| ---: | ---: |
| 10,000 | $80 |
| 100,000 | $800 |
| 1,000,000 | $8,000 |

These are projections for similar three-to-four-minute songs and two WAV outputs, before credits and allowances. Storage, retries, other GPUs, and application services change the total.

For an optional repeatability check, `python -m modal run benchmark_demucs.py` processes four local MP3/OPUS files in three rounds, with up to four concurrent workers. It requires local `ffprobe` from FFmpeg and saves measurements in `benchmark-results/`.

## Full tutorial

[Read the guide](docs/how-to-make-a-vocal-separation-engine-for-music.md), or open the [HTML version](docs/how-to-make-a-vocal-separation-engine-for-music.html) locally for section navigation and **Copy page as Markdown**.

After editing the guide, rebuild the HTML:

```bash
python -m pip install -r requirements-docs.txt
python docs/build_preview.py
```
