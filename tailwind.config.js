/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/input.html"],
  // content: ["./templates/**/*.html", "./src/**/*.js"],

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
