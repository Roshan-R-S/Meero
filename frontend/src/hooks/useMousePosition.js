import { useEffect, useState } from "react";

/**
 * Shared hook that tracks normalized mouse position (-1 to 1).
 * Replaces duplicate mousemove listeners in ThreeOrb and Background.
 */
const useMousePosition = () => {
  const [mouse, setMouse] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (event) => {
      setMouse({
        x: (event.clientX / window.innerWidth) * 2 - 1,
        y: -(event.clientY / window.innerHeight) * 2 + 1,
      });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return mouse;
};

export default useMousePosition;
