import { useEffect, useState } from "react";
import noiseSvg from "../assets/noise.svg";
import { useTheme } from "../hooks/useTheme";

const DEFAULT_TICKER_LINES = [
  "SYS.ONLINE // CORE ENGINE READY",
  "NET.LOCAL // NO EXTERNAL EGRESS",
  "MEM.ACTIVE // CONVERSATION LOADED",
  "STATUS.NOMINAL // ALL SYSTEMS GO",
];

const HologramOverlay = ({ lastMetadata = null }) => {
  const { theme } = useTheme();
  const tickerLines = theme.ticker || DEFAULT_TICKER_LINES;
  const [tickerIndex, setTickerIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTickerIndex((prev) => (prev + 1) % tickerLines.length);
    }, 3500);
    return () => clearInterval(interval);
  }, [tickerLines]);

  return (
    <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden select-none">
      {/* Live Telemetry Readout (Bottom-Left) */}
      {lastMetadata && (
        <div
          className="absolute bottom-16 left-6 font-mono text-[9px] leading-relaxed tracking-wider"
          style={{ color: theme.css["--th-text-dim"] }}
        >
          <div>ENGINE  · {(lastMetadata.engine || "—").toUpperCase()}</div>
          <div>LATENCY · {lastMetadata.latency_ms ? `${lastMetadata.latency_ms.toFixed(1)}ms` : "—"}</div>
          <div>INTENT  · {(lastMetadata.intent || "—").toUpperCase()}</div>
          <div>STATUS  · {lastMetadata.engine === "error" ? "FAULT" : "NOMINAL"}</div>
        </div>
      )}

      {/* System Status Ticker (Bottom-Center) */}
      <div
        className="absolute bottom-6 left-1/2 -translate-x-1/2 font-mono text-[9px] tracking-widest uppercase transition-all duration-500 text-center"
        style={{ color: theme.css["--th-text-dim"] }}
      >
        {tickerLines[tickerIndex]}
      </div>

      {/* Noise Texture Overlay */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{ backgroundImage: `url(${noiseSvg})` }}
      />
      <div className="absolute inset-0 shadow-[inset_0_0_150px_rgba(0,0,0,0.8)] pointer-events-none" />
    </div>
  );
};

export default HologramOverlay;
