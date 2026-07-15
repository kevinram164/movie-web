import shutil
import subprocess
from pathlib import Path


def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        raise RuntimeError(err[-2000:])


def transcode_to_hls(
    source: Path,
    out_dir: Path,
    *,
    crf: int = 22,
    hls_time: int = 6,
    subtitle: Path | None = None,
) -> Path:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    master = out_dir / "master.m3u8"
    seg = out_dir / "seg_%04d.ts"
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(crf),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-hls_time",
            str(hls_time),
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            str(seg),
            str(master),
        ]
    )

    if subtitle and subtitle.exists():
        vtt = out_dir / "subs.vi.vtt"
        try:
            run_ffmpeg(["-i", str(subtitle), str(vtt)])
        except RuntimeError as exc:
            print(f"[warn] subtitle convert failed: {exc}")

    return master
