/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,styl,css,pug}",
  ],
  safelist: [
    {
      pattern: /.*/, // Match all class names since plugins may use anything
    },
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'hsl(var(--primary-h), var(--primary-s), var(--primary-l))',
          hover: 'var(--primary-hover)',
          content: 'var(--primary-content)',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary-h), var(--secondary-s), var(--secondary-l))',
          hover: 'var(--secondary-hover)',
          content: 'var(--secondary-content)',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent-h), var(--accent-s), var(--accent-l))',
          hover: 'var(--accent-hover)',
          content: 'var(--accent-content)',
        },
      },
      zIndex: {
        '100': '100',
      },
    },
  },
  plugins: [],
  blocklist: ['collapse'], // disable because bootstrap uses it for something else
}
