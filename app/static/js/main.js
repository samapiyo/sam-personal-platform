document.addEventListener("DOMContentLoaded", () => {

  /* =========================
     MOBILE NAVIGATION
  ========================== */

  const menuToggle = document.querySelector("#menuToggle");
  const mainNav = document.querySelector("#mainNav");

  if (menuToggle && mainNav) {

    menuToggle.addEventListener("click", () => {
      const isOpen = mainNav.classList.toggle("open");

      menuToggle.setAttribute(
        "aria-expanded",
        isOpen ? "true" : "false"
      );

      menuToggle.setAttribute(
        "aria-label",
        isOpen ? "Close navigation menu" : "Open navigation menu"
      );

      menuToggle.textContent = isOpen ? "✕" : "☰";
    });

    // Close mobile menu after selecting a link
    mainNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        mainNav.classList.remove("open");
        menuToggle.setAttribute("aria-expanded", "false");
        menuToggle.setAttribute("aria-label", "Open navigation menu");
        menuToggle.textContent = "☰";
      });
    });

    // Close menu when switching back to desktop
    window.addEventListener("resize", () => {
      if (window.innerWidth > 768) {
        mainNav.classList.remove("open");
        menuToggle.setAttribute("aria-expanded", "false");
        menuToggle.setAttribute("aria-label", "Open navigation menu");
        menuToggle.textContent = "☰";
      }
    });
  }


  /* =========================
     PRODUCT SLIDER
  ========================== */

  const slider = document.querySelector("#productSlider .slides");
  const cards = [
    ...document.querySelectorAll("#productSlider .product-card")
  ];

  const dots = document.querySelector("#slideDots");
  const prev = document.querySelector("#prevSlide");
  const next = document.querySelector("#nextSlide");

  if (!slider || cards.length === 0) return;

  let index = 0;

  // Create slider dots
  if (dots) {
    cards.forEach((_, i) => {

      const dot = document.createElement("button");

      dot.type = "button";

      dot.setAttribute(
        "aria-label",
        `Show slide ${i + 1}`
      );

      dot.addEventListener("click", () => go(i));

      dots.appendChild(dot);
    });
  }

  function visibleCount() {

    if (window.innerWidth < 700) {
      return 1;
    }

    if (window.innerWidth < 1000) {
      return 2;
    }

    return 3;
  }

  function go(i) {

    const max = Math.max(
      0,
      cards.length - visibleCount()
    );

    index = Math.min(
      Math.max(i, 0),
      max
    );

    const cardWidth =
      cards[0].getBoundingClientRect().width + 20;

    slider.style.transform =
      `translateX(-${index * cardWidth}px)`;

    if (dots) {
      [...dots.children].forEach((dot, n) => {
        dot.classList.toggle(
          "active",
          n === index
        );
      });
    }
  }

  if (prev) {
    prev.addEventListener("click", () => {
      go(index - 1);
    });
  }

  if (next) {
    next.addEventListener("click", () => {
      go(index + 1);
    });
  }

  window.addEventListener("resize", () => {
    go(index);
  });

  go(0);

  // Automatic sliding
  setInterval(() => {

    const max = Math.max(
      0,
      cards.length - visibleCount()
    );

    go(index >= max ? 0 : index + 1);

  }, 4500);

});