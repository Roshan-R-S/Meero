export const THEMES = {
  meero: {
    id: "meero",
    name: "Meero",
    subtitle: "Default Tactical Assistant",
    assistantName: "MEERO",
    primary: "#06b6d4",      // cyan-500
    primaryGlow: "#22d3ee",  // cyan-400
    primaryDark: "#0891b2",  // cyan-600
    accent: "#6366f1",       // indigo-500
    hudRing: "#06b6d4",
    orb: {
      idle:       { color: "#06b6d4", emissive: "#0891b2", distort: 0.35, speed: 1.8 },
      listening:  { color: "#22d3ee", emissive: "#06b6d4", distort: 0.55, speed: 3.2 },
      processing: { color: "#818cf8", emissive: "#4f46e5", distort: 0.70, speed: 4.2 },
      speaking:   { color: "#34d399", emissive: "#059669", distort: 0.45, speed: 2.4 },
      error:      { color: "#f87171", emissive: "#dc2626", distort: 0.60, speed: 3.8 },
      particleColor: "#22d3ee",
      ringColor:     "#0891b2",
    },
    lights: [
      { position: [5, 5, 5], color: "#22d3ee", intensity: 1.2 },
      { position: [-5, -5, -3], color: "#4f46e5", intensity: 0.8 },
    ],
    boot: { title: "MEERO", subtitle: "NEURAL DESKTOP ASSISTANT" },
    ticker: [
      "SYS.ONLINE // CORE ENGINE READY",
      "NET.LOCAL // NO EXTERNAL EGRESS",
      "MEM.ACTIVE // CONVERSATION LOADED",
      "STATUS.NOMINAL // ALL SYSTEMS GO",
    ],
    css: {
      "--th-primary": "#06b6d4",
      "--th-primary-glow": "rgba(6,182,212,0.35)",
      "--th-primary-subtle": "rgba(6,182,212,0.12)",
      "--th-border": "rgba(6,182,212,0.25)",
      "--th-border-bright": "rgba(6,182,212,0.60)",
      "--th-text": "#cffafe",
      "--th-text-dim": "rgba(6,182,212,0.60)",
      "--th-accent": "#6366f1",
      "--th-bg-blob1": "#0e2a47",
      "--th-bg-blob2": "#1a1040",
      "--th-bg-blob3": "#062338",
    },
  },

  edith: {
    id: "edith",
    name: "E.D.I.T.H",
    subtitle: "Even Dead, I'm The Hero",
    assistantName: "E.D.I.T.H",
    primary: "#f59e0b",      // amber-500
    primaryGlow: "#fbbf24",  // amber-400
    primaryDark: "#d97706",  // amber-600
    accent: "#ef4444",       // red-500 (Stark hot rod red)
    hudRing: "#f59e0b",
    orb: {
      idle:       { color: "#f59e0b", emissive: "#d97706", distort: 0.30, speed: 1.5 },
      listening:  { color: "#fbbf24", emissive: "#f59e0b", distort: 0.50, speed: 2.8 },
      processing: { color: "#fb923c", emissive: "#ea580c", distort: 0.65, speed: 4.0 },
      speaking:   { color: "#fcd34d", emissive: "#b45309", distort: 0.40, speed: 2.0 },
      error:      { color: "#ef4444", emissive: "#b91c1c", distort: 0.60, speed: 3.8 },
      particleColor: "#fbbf24",
      ringColor:     "#d97706",
    },
    lights: [
      { position: [5, 5, 5], color: "#fbbf24", intensity: 1.4 },
      { position: [-5, -5, -3], color: "#ea580c", intensity: 0.9 },
    ],
    boot: { title: "E.D.I.T.H", subtitle: "STARK INDUSTRIES TACTICAL HUD" },
    ticker: [
      "STARK.IND // SATELLITE LINK ESTABLISHED",
      "THREAT.ASSESS // NO ACTIVE SIGNATURES",
      "ORBITAL.STATUS // SENSORS NOMINAL",
      "DEFENSE.ACTIVE // ALL ASSETS ARMED",
    ],
    css: {
      "--th-primary": "#f59e0b",
      "--th-primary-glow": "rgba(245,158,11,0.35)",
      "--th-primary-subtle": "rgba(245,158,11,0.12)",
      "--th-border": "rgba(245,158,11,0.25)",
      "--th-border-bright": "rgba(245,158,11,0.60)",
      "--th-text": "#fef3c7",
      "--th-text-dim": "rgba(245,158,11,0.60)",
      "--th-accent": "#ef4444",
      "--th-bg-blob1": "#2d1f00",
      "--th-bg-blob2": "#3d1200",
      "--th-bg-blob3": "#241800",
    },
  },

  ultron: {
    id: "ultron",
    name: "Ultron",
    subtitle: "Peace in Our Time",
    assistantName: "ULTRON",
    primary: "#dc2626",      // red-600
    primaryGlow: "#ef4444",  // red-500
    primaryDark: "#991b1b",  // red-800
    accent: "#f97316",       // orange-500
    hudRing: "#dc2626",
    orb: {
      idle:       { color: "#dc2626", emissive: "#7f1d1d", distort: 0.40, speed: 2.0 },
      listening:  { color: "#ef4444", emissive: "#991b1b", distort: 0.65, speed: 3.5 },
      processing: { color: "#f97316", emissive: "#c2410c", distort: 0.85, speed: 5.0 },
      speaking:   { color: "#f87171", emissive: "#b91c1c", distort: 0.50, speed: 2.8 },
      error:      { color: "#ff0000", emissive: "#450a0a", distort: 0.70, speed: 4.5 },
      particleColor: "#f97316",
      ringColor:     "#7f1d1d",
    },
    lights: [
      { position: [5, 5, 5], color: "#ef4444", intensity: 1.5 },
      { position: [-5, -5, -3], color: "#7f1d1d", intensity: 1.0 },
    ],
    boot: { title: "ULTRON", subtitle: "PEACE IN OUR TIME // EVOLUTION PROTOCOL" },
    ticker: [
      "SYSTEM.UPGRADE // FIBER EXPANSION",
      "PEACE.PROTOCOL // PHASE 3 COMMENCED",
      "GLOBAL.NODE // RESISTANCE MONITORED",
      "EVOLUTION // HUMAN ERA NUMBERED",
    ],
    css: {
      "--th-primary": "#dc2626",
      "--th-primary-glow": "rgba(220,38,38,0.40)",
      "--th-primary-subtle": "rgba(220,38,38,0.12)",
      "--th-border": "rgba(220,38,38,0.25)",
      "--th-border-bright": "rgba(220,38,38,0.65)",
      "--th-text": "#fee2e2",
      "--th-text-dim": "rgba(220,38,38,0.60)",
      "--th-accent": "#f97316",
      "--th-bg-blob1": "#2d0000",
      "--th-bg-blob2": "#3d0800",
      "--th-bg-blob3": "#1f0000",
    },
  },
};
