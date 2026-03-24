(() => {
  if (!("ontouchstart" in window)) return;

  const THRESHOLD = 80;
  const MAX_PULL = 120;
  let startY = 0;
  let pulling = false;
  let indicator = null;

  const isScrollableParent = (el) => {
    while (el && el !== document.body) {
      if (el.scrollTop > 0) return true;
      const style = getComputedStyle(el);
      const overflowY = style.overflowY;
      if ((overflowY === "auto" || overflowY === "scroll") && el.scrollHeight > el.clientHeight && el.scrollTop > 0) {
        return true;
      }
      el = el.parentElement;
    }
    return false;
  };

  const getIndicator = () => {
    if (indicator) return indicator;
    indicator = document.createElement("div");
    indicator.className = "ptr-indicator";
    indicator.setAttribute("aria-hidden", "true");
    document.body.appendChild(indicator);
    return indicator;
  };

  document.addEventListener("touchstart", (e) => {
    if (window.scrollY > 0) return;
    if (isScrollableParent(e.target)) return;
    startY = e.touches[0].clientY;
    pulling = true;
  }, { passive: true });

  document.addEventListener("touchmove", (e) => {
    if (!pulling) return;
    const y = e.touches[0].clientY;
    const diff = y - startY;
    if (diff < 0) {
      pulling = false;
      return;
    }
    if (window.scrollY > 0) {
      pulling = false;
      return;
    }
    const pull = Math.min(diff, MAX_PULL);
    const el = getIndicator();
    el.style.opacity = Math.min(pull / THRESHOLD, 1);
    el.style.transform = "translateX(-50%) translateY(" + (pull * 0.5) + "px)";
    if (pull >= THRESHOLD) {
      el.classList.add("ptr-ready");
    } else {
      el.classList.remove("ptr-ready");
    }
  }, { passive: true });

  document.addEventListener("touchend", () => {
    if (!pulling) return;
    pulling = false;
    const el = getIndicator();
    if (el.classList.contains("ptr-ready")) {
      el.classList.remove("ptr-ready");
      el.classList.add("ptr-loading");
      location.reload();
    } else {
      el.style.opacity = 0;
      el.style.transform = "translateX(-50%) translateY(0)";
    }
  }, { passive: true });
})();
