import Hls, { type ErrorData, type FragLoadedData } from "hls.js"

// QoE từ trình duyệt → POST /api/playback/events (movie-api ghi OTel metrics → Prometheus/Grafana).
// Server không suy ra được rebuffer/startup, chỉ player mới biết.

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/$/, "")
const ENDPOINT = `${API_BASE}/api/playback/events`
const FLUSH_MS = 15000
const MAX_SEGMENTS = 50
const MAX_TICK_MS = 2000

type Result = "success" | "failed" | "abandoned"

type Segment = { load_ms: number; ttfb_ms: number; bytes: number }

type Batch = {
  player: "hlsjs" | "native"
  startup_ms?: number
  result?: Result
  error?: string
  watch_ms: number
  rebuffer_ms: number
  rebuffer_count: number
  segments: Segment[]
}

export function attachPlaybackMetrics(video: HTMLVideoElement, hls?: Hls): () => void {
  const player: Batch["player"] = hls ? "hlsjs" : "native"
  let playRequestedAt: number | null = null
  let started = false
  let resultSent = false
  let stallStart: number | null = null
  let lastTick: number | null = null

  let pending: Batch = emptyBatch()

  function emptyBatch(): Batch {
    return { player, watch_ms: 0, rebuffer_ms: 0, rebuffer_count: 0, segments: [] }
  }

  function setResult(result: Result, error?: string) {
    if (resultSent) return
    resultSent = true
    pending.result = result
    if (error) pending.error = error.slice(0, 64)
  }

  function endStall(now: number) {
    if (stallStart === null) return
    pending.rebuffer_ms += now - stallStart
    stallStart = null
  }

  function tick(now: number) {
    if (lastTick !== null && started && stallStart === null && !video.paused) {
      pending.watch_ms += Math.min(now - lastTick, MAX_TICK_MS)
    }
    lastTick = now
  }

  function flush(useBeacon: boolean) {
    const now = performance.now()
    tick(now)
    if (stallStart !== null) {
      pending.rebuffer_ms += now - stallStart
      stallStart = now
    }
    const b = pending
    const empty =
      b.result === undefined && b.startup_ms === undefined && b.watch_ms < 1 && b.rebuffer_ms < 1 && b.segments.length === 0
    if (empty) return
    pending = emptyBatch()
    const body = JSON.stringify({
      ...b,
      watch_ms: Math.round(b.watch_ms),
      rebuffer_ms: Math.round(b.rebuffer_ms),
    })
    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }))
      return
    }
    fetch(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(
      () => undefined,
    )
  }

  const onPlay = () => {
    if (!started && playRequestedAt === null) playRequestedAt = performance.now()
  }

  const onPlaying = () => {
    const now = performance.now()
    if (!started) {
      started = true
      if (playRequestedAt !== null) pending.startup_ms = Math.round(now - playRequestedAt)
      setResult("success")
    }
    endStall(now)
    lastTick = now
  }

  const onWaiting = () => {
    // Seek cũng phát "waiting" — không tính là rebuffer
    if (!started || video.seeking || stallStart !== null) return
    tick(performance.now())
    stallStart = performance.now()
    pending.rebuffer_count += 1
  }

  const onSeeked = () => {
    stallStart = null
    lastTick = performance.now()
  }

  const onTimeUpdate = () => tick(performance.now())

  const onPause = () => {
    const now = performance.now()
    tick(now)
    endStall(now)
    lastTick = null
  }

  const onVideoError = () => {
    setResult("failed", `media_${video.error?.code ?? "unknown"}`)
    flush(false)
  }

  const onHlsError = (_: unknown, data: ErrorData) => {
    if (!data.fatal) return
    setResult("failed", data.details)
    flush(false)
  }

  const onFragLoaded = (_: unknown, data: FragLoadedData) => {
    if (data.frag.type !== "main") return
    const s = data.frag.stats
    const loadMs = s.loading.end - s.loading.start
    const ttfbMs = s.loading.first - s.loading.start
    if (!(loadMs > 0) || pending.segments.length >= MAX_SEGMENTS) return
    pending.segments.push({ load_ms: Math.round(loadMs), ttfb_ms: Math.max(0, Math.round(ttfbMs)), bytes: s.loaded })
  }

  const onPageHide = () => {
    if (playRequestedAt !== null && !started) setResult("abandoned")
    flush(true)
  }

  const onVisibility = () => {
    if (document.visibilityState === "hidden") flush(true)
  }

  video.addEventListener("play", onPlay)
  video.addEventListener("playing", onPlaying)
  video.addEventListener("waiting", onWaiting)
  video.addEventListener("seeked", onSeeked)
  video.addEventListener("timeupdate", onTimeUpdate)
  video.addEventListener("pause", onPause)
  video.addEventListener("error", onVideoError)
  hls?.on(Hls.Events.ERROR, onHlsError)
  hls?.on(Hls.Events.FRAG_LOADED, onFragLoaded)
  window.addEventListener("pagehide", onPageHide)
  document.addEventListener("visibilitychange", onVisibility)
  const timer = window.setInterval(() => flush(false), FLUSH_MS)

  return () => {
    window.clearInterval(timer)
    onPageHide()
    video.removeEventListener("play", onPlay)
    video.removeEventListener("playing", onPlaying)
    video.removeEventListener("waiting", onWaiting)
    video.removeEventListener("seeked", onSeeked)
    video.removeEventListener("timeupdate", onTimeUpdate)
    video.removeEventListener("pause", onPause)
    video.removeEventListener("error", onVideoError)
    hls?.off(Hls.Events.ERROR, onHlsError)
    hls?.off(Hls.Events.FRAG_LOADED, onFragLoaded)
    window.removeEventListener("pagehide", onPageHide)
    document.removeEventListener("visibilitychange", onVisibility)
  }
}
