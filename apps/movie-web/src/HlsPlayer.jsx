import { useEffect, useRef } from "react";
import Hls from "hls.js";

export default function HlsPlayer({ src, poster }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return undefined;

    let hls;
    if (Hls.isSupported()) {
      hls = new Hls({ enableWorker: true });
      hls.loadSource(src);
      hls.attachMedia(video);
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
    }

    return () => {
      if (hls) hls.destroy();
    };
  }, [src]);

  return (
    <div className="player-wrap">
      <video
        ref={videoRef}
        className="player"
        controls
        playsInline
        poster={poster || undefined}
      />
    </div>
  );
}
