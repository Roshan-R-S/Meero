import { motion as Motion } from "framer-motion";
import noiseSvg from "../assets/noise.svg";
const HologramOverlay = () => {
  return (
    <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden select-none">
      {/* 1. Rotating Data Rings (Center) */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] opacity-[0.08]">
        <Motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
          className="w-full h-full rounded-full border border-cyan-400 border-dashed"
        />
        <Motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
          className="absolute top-[10%] left-[10%] w-[80%] h-[80%] rounded-full border border-cyan-500 border-dotted"
        />
      </div>

      {/* 2. Corner Data Blocks */}
      {/* Top Left */}
      <div className="absolute top-10 left-10 flex flex-col gap-1 text-[10px] font-mono text-cyan-500/40 tracking-widest">
        <div>SYS.ROOT.User: ACTIVE</div>
        <div>MEM_ALLOC: 43.2%</div>
        <Motion.div
          animate={{ opacity: [0.2, 0.8, 0.2] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          NET_SPEED: 1.2 GB/s
        </Motion.div>
      </div>

      {/* Top Right */}
      <div className="absolute top-10 right-10 text-right">
        <div className="w-32 h-px bg-cyan-500/30 mb-2" />
        <div className="flex justify-end gap-1">
          {[1, 2, 3, 4].map((i) => (
            <Motion.div
              key={i}
              animate={{ height: [10, 20, 10] }}
              transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
              className="w-1 bg-cyan-500/30"
            />
          ))}
        </div>
      </div>

      {/* Bottom Left - Coordinates */}
      <div className="absolute bottom-10 left-10 font-mono text-[8px] text-cyan-500/30">
        <p>LAT: 32.443.12</p>
        <p>LNG: 88.102.33</p>
      </div>

      {/* 3. Scanning Grid Line */}
      <Motion.div
        animate={{ top: ["0%", "100%"], opacity: [0, 0.5, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
        className="absolute left-0 w-full h-px bg-cyan-400/20 shadow-[0_0_10px_rgba(34,211,238,0.2)]"
      />

      {/* 4. Vignette / Scanlines Texture */}
      <div
        className="absolute inset-0 opacity-[0.05]"
        style={{ backgroundImage: `url(${noiseSvg})` }}
      />
      <div className="absolute inset-0 shadow-[inset_0_0_150px_rgba(0,0,0,0.8)]" />
    </div>
  );
};

export default HologramOverlay;
