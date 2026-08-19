/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Named tokens — do not use raw hex in components, reference these.
        navy: {
          50: "#eef1f6",
          100: "#d3dae8",
          200: "#a7b6d1",
          300: "#7b91ba",
          400: "#4f6da3",
          500: "#2d4d84",
          600: "#1c3866",
          700: "#13294b",   // primary brand navy
          800: "#0d1d37",
          900: "#081324",
        },
        gold: {
          50: "#fbf6e7",
          100: "#f3e6b8",
          200: "#e6cd7d",
          300: "#d6b34f",
          400: "#c9a227",   // accent — used sparingly
          500: "#a8841c",
          600: "#846815",
        },
        maroon: {
          500: "#8b1e3f",   // alerts / admin-only actions
          600: "#6f1832",
        },
        saffron: "#FF9933",
        indiagreen: "#138808",
        parchment: "#f7f5f0", // app background
        ink: "#1b2230",       // primary text
      },
      fontFamily: {
        display: ["'Merriweather'", "Georgia", "serif"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(19,41,75,0.06), 0 4px 16px rgba(19,41,75,0.06)",
      },
      borderRadius: {
        sm2: "6px",
      },
    },
  },
  plugins: [],
};
