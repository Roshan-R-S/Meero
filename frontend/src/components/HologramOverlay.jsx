import { motion as Motion } from "framer-motion";
import { useEffect, useState } from "react";
import noiseSvg from "../assets/noise.svg";
import { useTheme } from "../hooks/useTheme";

const DEFAULT_TICKER_LINES = [
  "SYS.ONLINE // CORE ENGINE READY",
  "NET.LOCAL // NO EXTERNAL EGRESS",
  "MEM.ACTIVE // CONVERSATION LOADED",
  "STATUS.NOMINAL // ALL SYSTEMS GO",
];

const HologramOverlay = ({ state = "idle", lastMetadata = null }) => {
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
      {/* 1. Corner Bracket Markers (All 4 Corners) */}
      <div className="absolute top-6 left-6 w-6 h-6 border-t border-l" style={{ borderColor: theme.css["--th-border"] }} />
      <div className="absolute top-6 right-6 w-6 h-6 border-t border-r" style={{ borderColor: theme.css["--th-border"] }} />
      <div className="absolute bottom-6 left-6 w-6 h-6 border-b border-l" style={{ borderColor: theme.css["--th-border"] }} />
      <div className="absolute bottom-6 right-6 w-6 h-6 border-b border-r" style={{ borderColor: theme.css["--th-border"] }} />

      {/* 2. Live Telemetry Readout (Bottom-Left) */}
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

      {/* 3. Targeting Reticle (Center) */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 pointer-events-none">
        {["top-left", "top-right", "bottom-left", "bottom-right"].map((pos) => (
          <Motion.div
            key={pos}
            animate={{
              scale: state === "processing" ? [1, 0.85, 1] : 1,
              opacity: state === "idle" ? 0.15 : 0.6,
            }}
            transition={{ duration: 0.6, repeat: state === "processing" ? Infinity : 0 }}
            className={`absolute w-4 h-4
              ${pos.includes("top") ? "top-0 border-t" : "bottom-0 border-b"}
              ${pos.includes("left") ? "left-0 border-l" : "right-0 border-r"}
            `}
            style={{ borderColor: "var(--th-primary)" }}
          />
        ))}
      </div>

      {/* 4. 3 Orbiting Partial Arc Rings */}
      <svg className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] opacity-25 pointer-events-none">
        <Motion.circle
          cx="350"
          cy="350"
          r="180"
          fill="none"
          stroke={theme.hudRing}
          strokeWidth="1"
          strokeDasharray="60 300"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "350px 350px" }}
        />
        <Motion.circle
          cx="350"
          cy="350"
          r="260"
          fill="none"
          stroke={theme.hudRing}
          strokeWidth="0.75"
          strokeDasharray="80 440"
          animate={{ rotate: -360 }}
          transition={{ duration: 35, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "350px 350px" }}
        />
        <Motion.circle
          cx="350"
          cy="350"
          r="340"
          fill="none"
          stroke={theme.hudRing}
          strokeWidth="0.5"
          strokeDasharray="40 600"
          animate={{ rotate: 360 }}
          transition={{ duration: 50, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "350px 350px" }}
        />
      </svg>

      {/* 5. Dual Scan Lines */}
      <Motion.div
        className="absolute w-full h-[2px] opacity-40 pointer-events-none"
        style={{ background: `linear-gradient(90deg, transparent, ${theme.primary}, transparent)` }}
        animate={{ y: ["-10vh", "110vh"] }}
        transition={{ duration: 7, repeat: Infinity, ease: "linear" }}
      />
      <Motion.div
        className="absolute w-full h-[1px] opacity-20 pointer-events-none"
        style={{ background: `linear-gradient(90deg, transparent, ${theme.primary}, transparent)` }}
        animate={{ y: ["110vh", "-10vh"] }}
        transition={{ duration: 11, repeat: Infinity, ease: "linear" }}
      />

      {/* 6. System Status Ticker */}
      <div
        className="absolute bottom-6 left-1/2 -translate-x-1/2 font-mono text-[9px] tracking-widest uppercase transition-all duration-500 text-center"
        style={{ color: theme.css["--th-text-dim"] }}
      >
        {tickerLines[tickerIndex]}
      </div>

      {/* 7. Noise Texture Overlay */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{ backgroundImage: `url(${noiseSvg})` }}
      />
      <div className="absolute inset-0 shadow-[inset_0_0_150px_rgba(0,0,0,0.8)] pointer-events-none" />
    </div>
  );
};

export default HologramOverlay;
