/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // "Royal Blue" Palette
        board: {
          dark: '#0f172a',  // Deep Royal/Slate (Background)
          panel: '#1e293b', // Lighter panel background
          light: '#f0f9ff', // Sky White
          accent: '#38bdf8', // Sky Blue (Actions)
        },
        paper: {
          DEFAULT: '#ffffff', // Pure White
          dark: '#f1f5f9',    // Slate-50
        },
        ink: {
          DEFAULT: '#0f172a', // Navy Black
          light: '#64748b',   // Blue Gray
        }
      },
      fontFamily: {
        serif: ['Lora', 'Merriweather', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
