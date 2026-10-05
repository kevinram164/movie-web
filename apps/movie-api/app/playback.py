"""QoE từ player (lib/playback-metrics.ts) → OTel metrics → collector → Prometheus.

Tên Prometheus (exporter thêm hậu tố đơn vị):
  cinehome_playback_startup_seconds            histogram  thời gian bấm play → khung hình đầu
  cinehome_playback_sessions_total{result}     counter    success | failed | abandoned
  cinehome_playback_watch_seconds_total        counter    thời gian thực sự phát
  cinehome_playback_rebuffer_seconds_total     counter    thời gian đứng hình (không tính seek)
  cinehome_playback_rebuffer_events_total      counter
  cinehome_segment_load_seconds                histogram  tải 1 segment HLS (MinIO qua /media)
  cinehome_segment_ttfb_seconds                histogram
  cinehome_segment_bytes_total                 counter
Chỉ dùng label ít giá trị (player, result, error) — không gắn episode/user.
"""

from __future__ import annotations

import re
from typing import Literal

from opentelemetry import metrics
from pydantic import BaseModel, Field

_meter = metrics.get_meter("cinehome.playback", "1.0")

_startup = _meter.create_histogram("cinehome.playback.startup", unit="s", description="Play request to first frame")
_sessions = _meter.create_counter("cinehome.playback.sessions", description="Playback sessions by result")
_watch = _meter.create_counter("cinehome.playback.watch", unit="s", description="Time spent playing")
_rebuffer = _meter.create_counter("cinehome.playback.rebuffer", unit="s", description="Time stalled after start")
_rebuffer_events = _meter.create_counter("cinehome.playback.rebuffer.events", description="Stall events")
_seg_load = _meter.create_histogram("cinehome.segment.load", unit="s", description="HLS segment download time")
_seg_ttfb = _meter.create_histogram("cinehome.segment.ttfb", unit="s", description="HLS segment time to first byte")
_seg_bytes = _meter.create_counter("cinehome.segment.bytes", unit="By", description="HLS segment bytes downloaded")

_ERROR_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


class PlaybackSegment(BaseModel):
    load_ms: int = Field(ge=0, le=600_000)
    ttfb_ms: int = Field(ge=0, le=600_000)
    bytes: int = Field(ge=0, le=500_000_000)


class PlaybackEvents(BaseModel):
    player: Literal["hlsjs", "native"] = "hlsjs"
    startup_ms: int | None = Field(default=None, ge=0, le=600_000)
    result: Literal["success", "failed", "abandoned"] | None = None
    error: str = Field(default="", max_length=64)
    watch_ms: int = Field(default=0, ge=0, le=3_600_000)
    rebuffer_ms: int = Field(default=0, ge=0, le=3_600_000)
    rebuffer_count: int = Field(default=0, ge=0, le=10_000)
    segments: list[PlaybackSegment] = Field(default_factory=list, max_length=50)


def record_playback(ev: PlaybackEvents) -> None:
    attrs = {"player": ev.player}
    if ev.startup_ms is not None:
        _startup.record(ev.startup_ms / 1000, attrs)
    if ev.result:
        result_attrs = {**attrs, "result": ev.result}
        if ev.result == "failed":
            result_attrs["error"] = ev.error if _ERROR_RE.match(ev.error) else "other"
        _sessions.add(1, result_attrs)
    if ev.watch_ms:
        _watch.add(ev.watch_ms / 1000, attrs)
    if ev.rebuffer_ms:
        _rebuffer.add(ev.rebuffer_ms / 1000, attrs)
    if ev.rebuffer_count:
        _rebuffer_events.add(ev.rebuffer_count, attrs)
    for s in ev.segments:
        _seg_load.record(s.load_ms / 1000, attrs)
        _seg_ttfb.record(s.ttfb_ms / 1000, attrs)
        _seg_bytes.add(s.bytes, attrs)
