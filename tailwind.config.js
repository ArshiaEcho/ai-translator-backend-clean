/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#6B1C1D',
          50: '#F9E9E9',
          100: '#F0C9CA',
          200: '#E19C9D',
          300: '#CB6163',
          400: '#A62E30',
          500: '#6B1C1D',
          600: '#5E1819',
          700: '#501415',
          800: '#430F10',
          900: '#350C0D',
        },
        accent: {
          DEFAULT: '#9A1F21',
          50: '#FCEAEB',
          100: '#F6CACB',
          200: '#EB9A9C',
          300: '#DB6062',
          400: '#BC3134',
          500: '#9A1F21',
          600: '#881C1E',
          700: '#75181A',
          800: '#621415',
          900: '#4F1011',
        },
        gray: {
          50: '#F5F5F5',
          100: '#EBEBEB',
          200: '#D8D8D8',
          300: '#C0C0C0',
          400: '#A8A8A8',
          500: '#888888',
          600: '#6D6D6D',
          700: '#4A4A4A',
          800: '#333333',
          900: '#1A1A1A',
        },
      },
      boxShadow: {
        'custom': '0 4px 20px rgba(0, 0, 0, 0.08)',
        'custom-lg': '0 10px 30px rgba(0, 0, 0, 0.12)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};