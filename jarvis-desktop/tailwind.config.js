/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        void: "#020408",
        hud: {
          cyan: "#3ff0ff",
          cyanDim: "#0e6b78",
          blue: "#2e6fff",
          white: "#eaf9ff",
          orange: "#ff8a3d",
          orangeDim: "#7a3f14",
        },
      },
      fontFamily: {
        hud: ["Orbitron", "Rajdhani", "ui-sans-serif", "system-ui"],
        mono: ["Share Tech Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 12px rgba(63,240,255,0.55), 0 0 32px rgba(63,240,255,0.25)",
        glowOrange: "0 0 12px rgba(255,138,61,0.6), 0 0 32px rgba(255,138,61,0.3)",
      },
      keyframes: {
        "spin-slow": { to: { transform: "rotate(360deg)" } },
        "spin-slow-rev": { from: { transform: "rotate(360deg)" }, to: { transform: "rotate(0deg)" } },
        pulseGlow: {
          "0%, 100%": { opacity: 0.55, filter: "brightness(1)" },
          "50%": { opacity: 1, filter: "brightness(1.4)" },
        },
        sweep: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
      },
      animation: {
        "spin-slow": "spin-slow 18s linear infinite",
        "spin-slow-rev": "spin-slow-rev 26s linear infinite",
        "spin-slower": "spin-slow 40s linear infinite",
        pulseGlow: "pulseGlow 2.4s ease-in-out infinite",
        sweep: "sweep 4s linear infinite",
        scanline: "scanline 6s linear infinite",
      },
    },
  },
  plugins: [],
};
