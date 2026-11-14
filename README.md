# Video → MP4

A small web app: paste a video link, get the best-quality MP4.

วางลิงก์วิดีโอ แล้วแอปจะดาวน์โหลดเป็นไฟล์ MP4 คุณภาพสูงสุดให้

It uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to fetch the best video and
best audio streams, and [ffmpeg](https://ffmpeg.org/) to merge them into a
single `.mp4` file. Any site yt-dlp supports works, as do direct links to video
files.

> **Use responsibly.** Only download videos you own, that are in the public
> domain or under a licence that allows downloading, or that you have the
> rights holder's permission to download. Many sites' terms of service forbid
> downloading. You are responsible for how you use this tool.
>
> ใช้กับวิดีโอที่คุณมีสิทธิ์ดาวน์โหลดเท่านั้น

## Run it locally

You need **Python 3.10+** and **ffmpeg**.

Install ffmpeg:

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: `winget install ffmpeg` (or download from ffmpeg.org and add it to PATH)

Then:

```bash
git clone https://github.com/rodihemna-cyber/videodownload.git
cd videodownload
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>, paste a link, press **Download**, then **Save MP4**
when it's ready.

## Quality

By default the app picks the highest-quality **H.264 video + AAC audio**,
which plays everywhere (phones, Windows, QuickTime, TVs). On some sites, such
as YouTube, the very highest resolutions (above 1080p) are only offered as
VP9 or AV1. Tick **Highest resolution** to get those; they are still saved as
`.mp4`, but some older players can't play them.

## Settings

Environment variables, all optional:

| Variable | Default | What it does |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Address to listen on. Use `0.0.0.0` to reach it from other devices on your network. |
| `PORT` | `5000` | Port to listen on. |
| `DOWNLOAD_DIR` | system temp folder | Where files are stored while waiting to be saved. |
| `JOB_TTL_SECONDS` | `3600` | Finished downloads are deleted after this many seconds. |

## Troubleshooting

- **A site stopped working:** sites change often. Update yt-dlp with
  `pip install -U yt-dlp`.
- **"ffmpeg not found":** install ffmpeg (see above) and restart the app.

This app is meant for personal use on your own computer. It has no login or
rate limiting, so don't expose it to the public internet as is.

## How it works

- `POST /api/download` with `{"url": "...", "best_quality": false}` starts a
  download in a background thread and returns a `job_id`.
- `GET /api/jobs/<job_id>` returns the status and progress.
- `GET /api/jobs/<job_id>/file` returns the finished MP4.
