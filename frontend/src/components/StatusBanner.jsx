import { motion as Motion } from "framer-motion";
import { AlertTriangle, WifiOff } from "lucide-react";
export default function StatusBanner({ serverReachable, notice, onRetry }) {

  return (
    <>
      {/* HUD Alert Strip for transient notices */}
      {notice && (
        <Motion.div
          initial={{ y: -60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -60, opacity: 0 }}
          className="fixed top-6 left-1/2 -translate-x-1/2 z-50 min-w-[320px] max-w-md px-4 py-2.5 rounded border backdrop-blur-lg flex flex-col overflow-hidden shadow-2xl"
          style={{
            background: "rgba(10, 14, 23, 0.90)",
            borderColor: "var(--th-border-bright)",
            boxShadow: "0 0 20px var(--th-primary-glow)",
          }}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" style={{ color: "var(--th-primary)" }} />
            <span className="font-mono text-xs" style={{ color: "var(--th-text)" }}>
              [SYS_ALERT] {notice}
            </span>
          </div>
          <Motion.div
            initial={{ width: "100%" }}
            animate={{ width: "0%" }}
            transition={{ duration: 5, ease: "linear" }}
            className="h-[2px] mt-2"
            style={{ background: "var(--th-primary)" }}
          />
        </Motion.div>
      )}

      {/* Disconnection Warning & Red Screen Edge Vignette */}
      {!serverReachable && (
        <>
          <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded border border-red-500/60 bg-red-950/90 text-red-200 backdrop-blur-lg flex items-center gap-2 shadow-[0_0_20px_rgba(239,68,68,0.4)] font-mono text-xs">
            <WifiOff className="w-4 h-4 text-red-400 animate-pulse" />
            <span>CORE DISCONNECTED</span>
            {onRetry && (
              <button
                onClick={onRetry}
                className="ml-2 px-2 py-0.5 rounded bg-red-800 hover:bg-red-700 text-white underline font-bold"
              >
                RECONNECT
              </button>
            )}
          </div>

          <Motion.div
            animate={{ opacity: [0.3, 0.7, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="fixed inset-0 z-40 pointer-events-none"
            style={{ boxShadow: "inset 0 0 100px rgba(220, 38, 38, 0.5)" }}
          />
        </>
      )}
    </>
  );
}
