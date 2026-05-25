import { MeshDistortMaterial, Sphere } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import useMousePosition from "../hooks/useMousePosition";

const AnimatedCore = ({ state, sentiment }) => {
  const mesh = useRef();

  // Dynamic parameters based on state
  const config = useMemo(() => {
    switch (state) {
      case "listening":
        return { color: "#ef4444", speed: 2, distort: 0.6, scale: 2.5 }; // Red
      case "processing":
        return { color: "#eab308", speed: 4, distort: 0.8, scale: 2.0 }; // Gold
      case "speaking": {
        // Sentiment based coloring
        let color = "#10b981"; // Default Green
        if (sentiment === "negative") color = "#ef4444"; // Red
        if (sentiment === "neutral") color = "#3b82f6"; // Blue

        return { color, speed: 1.5, distort: 0.5, scale: 2.4 };
      }
      case "idle":
      default:
        return { color: "#06b6d4", speed: 1, distort: 0.4, scale: 2.2 }; // Cyan
    }
  }, [state, sentiment]);

  // Cache target vector to avoid allocating on every frame (60fps = 60 allocs/sec otherwise)
  const targetScale = useMemo(() => new THREE.Vector3(), []);

  useFrame((state, delta) => {
    if (mesh.current) {
      // Smoothly interpolate scale
      targetScale.set(config.scale, config.scale, config.scale);
      mesh.current.scale.lerp(targetScale, 0.1);
      // Rotate
      mesh.current.rotation.x += delta * 0.2;
      mesh.current.rotation.y += delta * 0.5;
    }
  });

  return (
    <Sphere ref={mesh} visible args={[1, 100, 200]} scale={2}>
      <MeshDistortMaterial
        color={config.color}
        attach="material"
        distort={config.distort}
        speed={config.speed}
        roughness={0.2}
        metalness={0.8}
        emissive={config.color}
        emissiveIntensity={0.5}
      />
    </Sphere>
  );
};

const ParticleRing = ({ count = 2000, color = "#ffffff" }) => {
  const points = useRef();

  // Generate random points on a sphere
  const particlesPosition = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const distance = 4.5;
    for (let i = 0; i < count; i++) {
      const theta = THREE.MathUtils.randFloatSpread(360);
      const phi = THREE.MathUtils.randFloatSpread(360);

      const x = distance * Math.sin(theta) * Math.cos(phi);
      const y = distance * Math.sin(theta) * Math.sin(phi);
      const z = distance * Math.cos(theta);

      positions.set([x, y, z], i * 3);
    }
    return positions;
  }, [count]);

  useFrame((state, delta) => {
    if (points.current) {
      points.current.rotation.y += delta * 0.1;
      points.current.rotation.z += delta * 0.05;
    }
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={particlesPosition.length / 3}
          array={particlesPosition}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color={color}
        sizeAttenuation
        transparent
        opacity={0.6}
      />
    </points>
  );
};

const ThreeOrb = ({ state, sentiment }) => {
  const mouse = useMousePosition();

  return (
    <div className="w-full h-full relative">
      <Canvas
        className="absolute inset-0 z-10"
        camera={{ position: [0, 0, 8], fov: 75 }}
      >
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1.5} />
        <pointLight position={[-10, -10, -10]} color="blue" intensity={1} />

        <group rotation={[mouse.y * 0.1, mouse.x * 0.1, 0]}>
          <AnimatedCore state={state} sentiment={sentiment} />
          <ParticleRing count={1500} />
        </group>
      </Canvas>
    </div>
  );
};

export default ThreeOrb;
