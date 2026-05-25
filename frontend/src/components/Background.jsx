import { motion as Motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";
import useMousePosition from "../hooks/useMousePosition";

const Background = () => {
  const mouse = useMousePosition();
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Sync shared hook values into motion values
  useEffect(() => {
    mouseX.set(mouse.x);
    mouseY.set(mouse.y);
  }, [mouse.x, mouse.y, mouseX, mouseY]);

  // Parallax transform values
  const x1 = useTransform(mouseX, [-1, 1], [-50, 50]);
  const y1 = useTransform(mouseY, [-1, 1], [-50, 50]);

  const x2 = useTransform(mouseX, [-1, 1], [30, -30]);
  const y2 = useTransform(mouseY, [-1, 1], [30, -30]);

  return (
    <div className="fixed inset-0 z-[-1] overflow-hidden bg-black">
      {/* Deep Space Gradients */}
      <Motion.div
        style={{ x: x1, y: y1 }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.5, 0.8, 0.5],
        }}
        transition={{
          scale: { duration: 12, repeat: Infinity, ease: "easeInOut" },
          opacity: { duration: 12, repeat: Infinity, ease: "easeInOut" },
        }}
        className="absolute top-[-20%] left-[-10%] w-[70vw] h-[70vw] rounded-full bg-blue-900/40 blur-[120px]"
      />

      <Motion.div
        style={{ x: x2, y: y2 }}
        animate={{
          scale: [1, 1.5, 1],
          opacity: [0.4, 0.7, 0.4],
        }}
        transition={{
          scale: { duration: 15, repeat: Infinity, ease: "easeInOut" },
          opacity: {
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2,
          },
        }}
        className="absolute bottom-[-20%] right-[-10%] w-[70vw] h-[70vw] rounded-full bg-cyan-900/30 blur-[120px]"
      />

      <Motion.div
        style={{ x: x1, y: y2 }} // Mixed
        animate={{
          scale: [1, 1.1, 1],
        }}
        transition={{
          scale: { duration: 20, repeat: Infinity, ease: "easeInOut" },
        }}
        className="absolute top-[40%] left-[30%] w-[40vw] h-[40vw] rounded-full bg-indigo-900/20 blur-[100px]"
      />
    </div>
  );
};

export default Background;
