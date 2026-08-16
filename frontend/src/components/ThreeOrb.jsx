import { MeshDistortMaterial, Sphere } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import useMousePosition from "../hooks/useMousePosition";

/**
 * AnimatedCore — the central distorted sphere.
 *
 * When state === "listening", micEnergyLevel (0–1) is used to:
 *  - Boost the distort amount (blob pulsing) in real-time with speech energy
 *  - Slightly expand the scale, giving a "breathing with the voice" effect
 *  - Increase emissive intensity for a brighter glow during loud speech
 */
const AnimatedCore = ({ state, sentiment, micEnergyLevel = 0 }) => {
  const mesh = useRef();

  // Base config driven by state
  const baseConfig = useMemo(() => {
    switch (state) {
      case "listening":
        return { color: "#ef4444", speed: 2, distort: 0.6, scale: 2.5, emissive: 0.5 }; // Red
      case "processing":
        return { color: "#eab308", speed: 4, distort: 0.8, scale: 2.0, emissive: 0.6 }; // Gold
      case "speaking": {
        let color = "#10b981"; // Default Green
        if (sentiment === "negative") color = "#ef4444"; // Red
        if (sentiment === "neutral") color = "#f59e0b";  // Amber
        return { color, speed: 1.5, distort: 0.5, scale: 2.4, emissive: 0.5 };
      }
      case "idle":
      default:
        return { color: "#06b6d4", speed: 1, distort: 0.4, scale: 2.2, emissive: 0.4 }; // Cyan
    }
  }, [state, sentiment]);

  // Compute mic-reactive overrides (only meaningful while listening)
  // micEnergyLevel: 0 (silence) → 1 (loud speech)
  const energyBoost = state === "listening" ? micEnergyLevel : 0;

  const targetScale = useMemo(() => new THREE.Vector3(), []);
  const distortRef = useRef(baseConfig.distort);
  const emissiveRef = useRef(baseConfig.emissive);

  useFrame((_state, delta) => {
    if (!mesh.current) return;

    // Smoothly lerp scale — energy expands the orb slightly (up to +0.6 extra)
    const targetScaleValue = baseConfig.scale + energyBoost * 0.6;
    targetScale.set(targetScaleValue, targetScaleValue, targetScaleValue);
    mesh.current.scale.lerp(targetScale, 0.12);

    // Smoothly lerp distort and emissive via refs (material props)
    distortRef.current = THREE.MathUtils.lerp(
      distortRef.current,
      baseConfig.distort + energyBoost * 0.4,
      0.15,
    );
    emissiveRef.current = THREE.MathUtils.lerp(
      emissiveRef.current,
      baseConfig.emissive + energyBoost * 0.5,
      0.15,
    );

    // Apply directly to material for per-frame updates without re-render
    if (mesh.current.material) {
      mesh.current.material.distort = distortRef.current;
      mesh.current.material.emissiveIntensity = emissiveRef.current;
    }

    // Rotate
    mesh.current.rotation.x += delta * 0.2;
    mesh.current.rotation.y += delta * 0.5;
  });

  return (
    <Sphere ref={mesh} visible args={[1, 100, 200]} scale={2}>
      <MeshDistortMaterial
        color={baseConfig.color}
        attach="material"
        distort={baseConfig.distort}
        speed={baseConfig.speed}
        roughness={0.2}
        metalness={0.8}
        emissive={baseConfig.color}
        emissiveIntensity={baseConfig.emissive}
      />
    </Sphere>
  );
};

/**
 * ParticleRing — ambient particle cloud orbiting the orb.
 *
 * When listening, particles rotate faster proportional to micEnergyLevel,
 * giving a sense that the orb is "excited" by incoming audio.
 */
const ParticleRing = ({ count = 2000, color = "#ffffff", energyBoost = 0 }) => {
  const points = useRef();

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

  useFrame((_state, delta) => {
    if (points.current) {
      // Base rotation + energy-driven acceleration
      points.current.rotation.y += delta * (0.1 + energyBoost * 0.25);
      points.current.rotation.z += delta * (0.05 + energyBoost * 0.1);
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
        opacity={0.6 + energyBoost * 0.25}
      />
    </points>
  );
};

const ThreeOrb = ({ state, sentiment, micEnergyLevel = 0 }) => {
  const mouse = useMousePosition();
  const energyBoost = state === "listening" ? micEnergyLevel : 0;

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
          <AnimatedCore state={state} sentiment={sentiment} micEnergyLevel={micEnergyLevel} />
          <ParticleRing count={1500} energyBoost={energyBoost} />
        </group>
      </Canvas>
    </div>
  );
};

export default ThreeOrb;
