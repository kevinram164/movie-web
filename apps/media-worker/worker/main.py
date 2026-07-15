import json
import shutil
import time
import traceback
from pathlib import Path

from worker.config import settings
from worker.db import set_episode_status
from worker.minio_ops import download_object, upload_dir
from worker.redis_client import get_redis_client
from worker.transcode import transcode_to_hls


def get_redis():
    return get_redis_client(
        settings.redis_url,
        sentinel_master=settings.redis_sentinel_master,
        sentinel_port=settings.redis_sentinel_port,
    )


def process_job(job: dict) -> None:
    episode_id = int(job["episode_id"])
    raw_key = job["raw_key"]
    subtitle_raw_key = (job.get("subtitle_raw_key") or "").strip()
    hls_key = job.get("hls_key") or ""
    series_slug = job.get("series_slug") or "unknown"
    season_number = int(job.get("season_number") or 1)
    episode_number = int(job.get("episode_number") or 1)

    ep_code = f"s{season_number:02d}e{episode_number:02d}"
    prefix = f"{series_slug}/{ep_code}"
    if not hls_key:
        hls_key = f"{prefix}/master.m3u8"

    work = Path(settings.work_dir) / f"ep-{episode_id}-{int(time.time())}"
    work.mkdir(parents=True, exist_ok=True)

    try:
        set_episode_status(episode_id, "PROCESSING")
        ext = Path(raw_key).suffix or ".mp4"
        source = work / f"source{ext}"
        print(f"[job] ep={episode_id} download raw/{raw_key}")
        download_object(settings.minio_bucket_raw, raw_key, source)

        subtitle = None
        if subtitle_raw_key:
            subtitle = work / "source.srt"
            try:
                download_object(settings.minio_bucket_raw, subtitle_raw_key, subtitle)
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] subtitle download: {exc}")
                subtitle = None

        out_dir = work / "hls"
        print(f"[job] ep={episode_id} ffmpeg → {prefix}/")
        transcode_to_hls(
            source,
            out_dir,
            crf=settings.ffmpeg_crf,
            hls_time=settings.hls_time,
            subtitle=subtitle,
        )

        print(f"[job] ep={episode_id} upload movies/{prefix}/")
        upload_dir(out_dir, settings.minio_bucket_movies, prefix)
        set_episode_status(episode_id, "READY", hls_key=hls_key)
        print(f"[job] ep={episode_id} READY {hls_key}")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)[:1900]
        print(f"[job] ep={episode_id} FAILED: {msg}")
        traceback.print_exc()
        set_episode_status(episode_id, "FAILED", error_message=msg)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> None:
    Path(settings.work_dir).mkdir(parents=True, exist_ok=True)
    r = get_redis()
    print(f"[media-worker] queue={settings.media_queue} redis ok")
    while True:
        item = r.brpop(settings.media_queue, timeout=5)
        if not item:
            continue
        _, payload = item
        try:
            job = json.loads(payload)
        except json.JSONDecodeError:
            print(f"[warn] bad job payload: {payload[:200]}")
            continue
        try:
            process_job(job)
        except Exception:  # noqa: BLE001
            # Đã set FAILED trong process_job; tiếp tục job kế
            continue


if __name__ == "__main__":
    main()
