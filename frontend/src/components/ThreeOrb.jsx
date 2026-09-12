import { MeshDistortMaterial, Sphere } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import useMousePosition from "../hooks/useMousePosition";
import { useTheme } from "../hooks/useTheme";

const usePrefersReducedMotion = () => {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const listener = (e) => setReduced(e.matches);
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  return reduced;
};

/**
 * AnimatedCore — the central distorted sphere.
 *
 * When state === "listening", micEnergyLevel (0–1) is used to:
 *  - Boost the distort amount (blob pulsing) in real-time with speech energy
 *  - Slightly expand the scale, giving a "breathing with the voice" effect
 *  - Increase emissive intensity for a brighter glow during loud speech
 */
const AnimatedCore = ({ state, sentiment, micEnergyLevel = 0, reducedMotion = false }) => {
  const mesh = useRef();
  const { theme } = useTheme();
  const orbConfig = theme.orb[state] || theme.orb.idle;

  // Base config driven by theme & state
  const baseConfig = useMemo(() => {
    let color = orbConfig.color;
    if (state === "speaking") {
      if (sentiment === "negative") color = theme.orb.error?.color || "#ef4444";
      if (sentiment === "neutral") color = orbConfig.color;
    }
    return {
      color,
      emissive: orbConfig.emissive,
      speed: orbConfig.speed,
      distort: orbConfig.distort,
      scale: state === "listening" ? 2.5 : state === "processing" ? 2.0 : 2.2,
      emissiveIntensity: 0.5,
    };
  }, [state, sentiment, orbConfig, theme]);

  // Compute mic-reactive overrides (only meaningful while listening)
  const energyBoost = state === "listening" && !reducedMotion ? micEnergyLevel : 0;

  const targetScale = useMemo(() => new THREE.Vector3(), []);
  const distortRef = useRef(baseConfig.distort);
  const emissiveRef = useRef(baseConfig.emissive);

  useFrame((_state, delta) => {
    if (!mesh.current) return;

    if (reducedMotion) {
      targetScale.set(baseConfig.scale, baseConfig.scale, baseConfig.scale);
      mesh.current.scale.copy(targetScale);
      if (mesh.current.material) {
        mesh.current.material.distort = 0.1;
        mesh.current.material.emissiveIntensity = baseConfig.emissive;
      }
      return;
    }

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
        distort={reducedMotion ? 0.1 : baseConfig.distort}
        speed={reducedMotion ? 0 : baseConfig.speed}
        roughness={0.2}
        metalness={0.8}
        emissive={baseConfig.color}
        emissiveIntensity={baseConfig.emissive}
      />
    </Sphere>
  );
};

const createSpherePositions = (count, distance = 4.5) => {
  const positions = new Float32Array(count * 3);
  let seed = 123456789;
  const lcg = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  for (let i = 0; i < count; i++) {
    const u = lcg();
    const v = lcg();
    const theta = u * 2.0 * Math.PI;
    const phi = Math.acos(2.0 * v - 1.0);
    const r = distance + (lcg() - 0.5) * 0.5;
    const x = r * Math.sin(phi) * Math.cos(theta);
    const y = r * Math.sin(phi) * Math.sin(theta);
    const z = r * Math.cos(phi);
    positions.set([x, y, z], i * 3);
  }
  return positions;
};

/**
 * ParticleRing — ambient particle cloud orbiting the orb.
 * Uses uniform spherical coordinate sampling for true 3D orbital cloud.
 */
const ParticleRing = ({ count = 1500, color, energyBoost = 0, reducedMotion = false }) => {
  const points = useRef();
  const { theme } = useTheme();
  const particleColor = color || theme.orb.particleColor || "#22d3ee";

  const particlesPosition = useMemo(() => {
    return createSpherePositions(count, 4.5);
  }, [count]);

  useFrame((_state, delta) => {
    if (points.current && !reducedMotion) {
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
        color={particleColor}
        sizeAttenuation
        transparent
        opacity={0.6 + energyBoost * 0.25}
      />
    </points>
  );
};

const OrbScene = ({ state, sentiment, micEnergyLevel, mouse, reducedMotion }) => {
  const groupRef = useRef();
  const energyBoost = state === "listening" && !reducedMotion ? micEnergyLevel : 0;

  useFrame(() => {
    if (!groupRef.current) return;
    const targetX = mouse.y * 0.1;
    const targetY = mouse.x * 0.1;

    if (reducedMotion) {
      groupRef.current.rotation.x = targetX;
      groupRef.current.rotation.y = targetY;
    } else {
      // Damped smooth inertia for mouse tracking
      groupRef.current.rotation.x = THREE.MathUtils.lerp(groupRef.current.rotation.x, targetX, 0.08);
      groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, targetY, 0.08);
    }
  });

  return (
    <group ref={groupRef}>
      <AnimatedCore
        state={state}
        sentiment={sentiment}
        micEnergyLevel={micEnergyLevel}
        reducedMotion={reducedMotion}
      />
      <ParticleRing
        count={1500}
        energyBoost={energyBoost}
        reducedMotion={reducedMotion}
      />
    </group>
  );
};

const ThreeOrb = ({ state, sentiment, micEnergyLevel = 0 }) => {
  const mouse = useMousePosition();
  const reducedMotion = usePrefersReducedMotion();
  const { theme } = useTheme();

  return (
    <div className="w-full h-full relative">
      <Canvas
        className="absolute inset-0 z-10"
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 8], fov: 75 }}
      >
        <ambientLight intensity={0.5} />
        {theme.lights ? (
          theme.lights.map((l, i) => (
            <pointLight key={i} position={l.position} color={l.color} intensity={l.intensity} />
          ))
        ) : (
          <>
            <pointLight position={[10, 10, 10]} intensity={1.5} />
            <pointLight position={[-10, -10, -10]} color="blue" intensity={1} />
          </>
        )}

        <Suspense fallback={null}>
          <OrbScene
            state={state}
            sentiment={sentiment}
            micEnergyLevel={micEnergyLevel}
            mouse={mouse}
            reducedMotion={reducedMotion}
          />
        </Suspense>
      </Canvas>
    </div>
  );
};

export default ThreeOrb;
