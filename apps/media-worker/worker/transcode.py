import shutil
import subprocess
from pathlib import Path


def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        raise RuntimeError(err[-2000:])


def _write_subs_playlist(out_dir: Path, vtt_name: str = "subs.vi.vtt") -> Path:
    """HLS WebVTT playlist (1 file VTT cho cả tập)."""
    path = out_dir / "subs.vi.m3u8"
    path.write_text(
        "\n".join(
            [
                "#EXTM3U",
                "#EXT-X-VERSION:3",
                "#EXT-X-TARGETDURATION:99999",
                "#EXT-X-MEDIA-SEQUENCE:0",
                "#EXT-X-PLAYLIST-TYPE:VOD",
                "#EXTINF:99999.0,",
                vtt_name,
                "#EXT-X-ENDLIST",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _inject_subtitles_into_master(master: Path, subs_playlist: str = "subs.vi.m3u8") -> None:
    """Thêm EXT-X-MEDIA + SUBTITLES= vào master.m3u8."""
    text = master.read_text(encoding="utf-8")
    if "TYPE=SUBTITLES" in text:
        return
    lines = text.splitlines()
    out: list[str] = []
    media_line = (
        '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Vietnamese",'
        'DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="vi",'
        f'URI="{subs_playlist}"'
    )
    inserted_media = False
    for line in lines:
        if line.startswith("#EXTM3U") and not inserted_media:
            out.append(line)
            out.append(media_line)
            inserted_media = True
            continue
        if line.startswith("#EXT-X-STREAM-INF:") and "SUBTITLES=" not in line:
            line = line.rstrip() + ',SUBTITLES="subs"'
        out.append(line)
    if not inserted_media:
        out.insert(0, "#EXTM3U")
        out.insert(1, media_line)
    master.write_text("\n".join(out) + "\n", encoding="utf-8")


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
            "160k",
            # Browsers can't play 5.1 AAC from web-dl sources; force stereo
            "-ac",
            "2",
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
        converted = False
        for enc in ("UTF-8", "CP1252", "ISO-8859-1", "WINDOWS-1258", "CP1258"):
            try:
                run_ffmpeg(["-sub_charenc", enc, "-i", str(subtitle), str(vtt)])
                if vtt.exists() and vtt.stat().st_size > 0:
                    converted = True
                    break
            except RuntimeError:
                continue
        if converted:
            _write_subs_playlist(out_dir, vtt.name)
            _inject_subtitles_into_master(master)
            print(f"[transcode] subtitles → {vtt.name}")
        else:
            print(f"[warn] subtitle convert failed (charset): {subtitle.name}")

    return master
