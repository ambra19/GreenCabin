/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./input.html", "./src/**/*.js"],
  theme: {
    extend: {
      fontFamily: {
        herofont: ["Montserrat", "serif"],
        secfont: ["Lora", "serif"],
        Primaryfont: ["Inter", "serif"],
      },
    },
  },
  plugins: [],
};
