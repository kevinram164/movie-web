#!/usr/bin/env bash
# Transcode MP4/MKV → HLS rồi upload MinIO
# Usage:
#   ./scripts/transcode-upload.sh /path/to/movie.mp4 night-drive
# Env:
#   MINIO_ALIAS=local (mc alias đã set)
#   BUCKET=movies

set -euo pipefail

SRC="${1:?file video}"
SLUG="${2:?slug thư mục trên MinIO, vd night-drive}"
BUCKET="${BUCKET:-movies}"
OUT_DIR="${TMPDIR:-/tmp}/hls-${SLUG}"

command -v ffmpeg >/dev/null || { echo "cần ffmpeg"; exit 1; }
command -v mc >/dev/null || { echo "cần mc (MinIO client)"; exit 1; }

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo "==> ffmpeg → HLS: $OUT_DIR"
ffmpeg -y -i "$SRC" \
  -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k \
  -hls_time 6 -hls_playlist_type vod \
  -hls_segment_filename "$OUT_DIR/seg_%04d.ts" \
  "$OUT_DIR/master.m3u8"

echo "==> upload mc → ${BUCKET}/${SLUG}/"
mc mirror --overwrite "$OUT_DIR" "${MINIO_ALIAS:-local}/${BUCKET}/${SLUG}"

echo "OK: object key = ${SLUG}/master.m3u8"
echo "API demo seed dùng hls_key=${SLUG}/master.m3u8 với slug demo tương ứng."
