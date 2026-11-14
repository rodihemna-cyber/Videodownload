"""Paste a link, get a high-quality MP4.

A small Flask app around yt-dlp. Each download runs in a background thread;
the browser polls for progress and then fetches the finished MP4.
"""

import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file
import yt_dlp

DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", tempfile.gettempdir())) / "video-downloader"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", 3600))

# Best video + best audio, preferring streams that remux cleanly into MP4
# (H.264/AVC video + AAC/M4A audio). Falls back to the best of anything,
# which is then remuxed or re-encoded to MP4 by ffmpeg.
FORMAT = (
    "bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/"
    "bestvideo+bestaudio/"
    "best"
)

app = Flask(__name__)
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def _update(job_id: str, **fields) -> None:
    with jobs_lock:
        jobs[job_id].update(fields)


def _cleanup_old_jobs() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    with jobs_lock:
        old = [jid for jid, j in jobs.items() if j["created"] < cutoff]
        for jid in old:
            jobs.pop(jid)
    for jid in old:
        shutil.rmtree(DOWNLOAD_DIR / jid, ignore_errors=True)


def _run_download(job_id: str, url: str, best_quality: bool) -> None:
    job_dir = DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            pct = (d.get("downloaded_bytes", 0) / total * 100) if total else None
            _update(job_id, status="downloading", progress=pct)
        elif d["status"] == "finished":
            _update(job_id, status="processing", progress=100)

    opts = {
        "format": "bestvideo+bestaudio/best" if best_quality else FORMAT,
        "merge_output_format": "mp4",
        # Make sure the final file is MP4 even when the source was a single
        # non-MP4 stream (for example WebM).
        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
        "outtmpl": str(job_dir / "%(title).150B.%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": False,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        files = sorted(job_dir.glob("*.mp4"), key=lambda p: p.stat().st_size, reverse=True)
        if not files:
            raise RuntimeError("No MP4 file was produced.")
        _update(
            job_id,
            status="done",
            progress=100,
            file=str(files[0]),
            filename=files[0].name,
            title=info.get("title"),
            resolution=f'{info["width"]}x{info["height"]}' if info.get("width") and info.get("height") else None,
        )
    except Exception as exc:  # yt-dlp raises many error types
        message = str(exc).replace("ERROR: ", "", 1)
        _update(job_id, status="error", error=message)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/download")
def start_download():
    _cleanup_old_jobs()
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify(error="Please paste a full link starting with http:// or https://"), 400

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "progress": 0, "created": time.time()}
    threading.Thread(
        target=_run_download,
        args=(job_id, url, bool(data.get("best_quality"))),
        daemon=True,
    ).start()
    return jsonify(job_id=job_id), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            abort(404)
        return jsonify({k: v for k, v in job.items() if k != "file"})


@app.get("/api/jobs/<job_id>/file")
def job_file(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        abort(404)
    return send_file(job["file"], mimetype="video/mp4", as_attachment=True,
                     download_name=job["filename"])


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)))
