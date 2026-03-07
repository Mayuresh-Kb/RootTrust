/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#2E7D32",
          50: "#E8F5E9",
          100: "#C8E6C9",
          200: "#A5D6A7",
          300: "#81C784",
          400: "#66BB6A",
          500: "#4CAF50",
          600: "#43A047",
          700: "#388E3C",
          800: "#2E7D32",
          900: "#1B5E20",
        },
        secondary: {
          DEFAULT: "#66BB6A",
          light: "#81C784",
          dark: "#43A047",
        },
        accent: {
          DEFAULT: "#FFB300",
          light: "#FFC107",
          dark: "#FF8F00",
        },
        background: {
          DEFAULT: "#F5F7FA",
          light: "#FFFFFF",
          dark: "#E8F5E9",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};
