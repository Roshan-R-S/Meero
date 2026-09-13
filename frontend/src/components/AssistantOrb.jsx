import { motion as Motion } from "framer-motion";
import { useTheme } from "../hooks/useTheme";
import ThreeOrb from "./ThreeOrb";

export default function AssistantOrb({ state, sentiment, micEnergyLevel = 0 }) {
  const { theme } = useTheme();

  return (
    <div className="relative flex items-center justify-center w-[340px] h-[340px] sm:w-[400px] sm:h-[400px] select-none">
      {/* Concentric Orbiting HUD Rings directly aligned with the Orb */}
      <svg
        className="absolute inset-0 w-full h-full opacity-40 pointer-events-none"
        viewBox="0 0 400 400"
      >
        <Motion.circle
          cx="200"
          cy="200"
          r="125"
          fill="none"
          stroke={theme?.hudRing || "var(--th-primary)"}
          strokeWidth="1"
          strokeDasharray="40 160"
          animate={{ rotate: 360 }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "200px 200px" }}
        />
        <Motion.circle
          cx="200"
          cy="200"
          r="155"
          fill="none"
          stroke={theme?.hudRing || "var(--th-primary)"}
          strokeWidth="0.75"
          strokeDasharray="60 240"
          animate={{ rotate: -360 }}
          transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "200px 200px" }}
        />
        <Motion.circle
          cx="200"
          cy="200"
          r="185"
          fill="none"
          stroke={theme?.hudRing || "var(--th-primary)"}
          strokeWidth="0.5"
          strokeDasharray="30 320"
          animate={{ rotate: 360 }}
          transition={{ duration: 55, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "200px 200px" }}
        />
      </svg>

      {/* 3D Orb Component */}
      <div className="relative z-10 w-full h-full flex items-center justify-center">
        <ThreeOrb state={state} sentiment={sentiment} micEnergyLevel={micEnergyLevel} />
      </div>
    </div>
  );
}
