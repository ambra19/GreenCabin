const faqs = document.querySelectorAll(".faq");
faqs.forEach((item) => {
  const question = item.querySelector(".question");
  const answer = item.querySelector(".answer");
  const openicon = item.querySelector(".openicon");
  const closedicon = item.querySelector(".closedicon");
  question.addEventListener("click", () => {
    faqs.forEach((otherfaq) => {
      if (otherfaq !== item) {
        const otheranswer = otherfaq.querySelector(".answer");
        const otherclosedicon = otherfaq.querySelector(".closedicon");
        const otheropenicon = otherfaq.querySelector(".openicon");
        otheranswer.classList.add("hidden");
        otherclosedicon.classList.remove("hidden");
        otheropenicon.classList.add("hidden");
      }
    });

    if (answer.classList.contains("hidden")) {
      openicon.classList.remove("hidden");
      closedicon.classList.add("hidden");
      answer.classList.remove("hidden");
      answer.classList.add("flex");
    } else {
      openicon.classList.add("hidden");
      closedicon.classList.remove("hidden");
      answer.classList.add("hidden");
      answer.classList.remove("flex");
    }
  });
});
