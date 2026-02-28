(() => {
  const config = window.__APP_TOUR__ || {};
  if (!config.enabled) {
    return;
  }

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";

  const baseSteps = [
    {
      selector: '[data-tour="nav-dashboard"]',
      title: "Dashboard",
      text: "Aca ves el estado general del taller y alertas rapidas.",
    },
    {
      selector: '[data-tour="nav-clients"]',
      title: "Clientes",
      text: "Registra y administra los datos de tus clientes.",
    },
    {
      selector: '[data-tour="nav-bicycles"]',
      title: "Bicicletas",
      text: "Asocia bicicletas a clientes para luego crear trabajos.",
    },
    {
      selector: '[data-tour="nav-services"]',
      title: "Service",
      text: "Configura tipos de service y precios base para tus trabajos.",
    },
    {
      selector: '[data-tour="nav-jobs"]',
      title: "Trabajos",
      text: "Gestiona ordenes, estados y seguimiento de cada ingreso.",
    },
    {
      selector: '[data-tour="action-new-job"]',
      title: "Nuevo trabajo",
      text: "Desde aqui puedes crear rapidamente una nueva orden.",
    },
  ];

  const ownerSteps = [
    {
      selector: '[data-tour="nav-owner-config"]',
      title: "Configuracion",
      text: "Desde este menu accedes a personalizacion, seguridad, usuarios y onboarding.",
    },
  ];

  const steps = config.role === "owner" ? [...baseSteps, ...ownerSteps] : baseSteps;

  let activeSteps = [];
  let currentIndex = 0;
  let highlightedNode = null;

  const overlay = document.createElement("div");
  overlay.className = "tour-overlay";

  const popover = document.createElement("section");
  popover.className = "tour-popover";
  popover.setAttribute("role", "dialog");
  popover.setAttribute("aria-modal", "true");
  popover.innerHTML = `
    <header class="tour-popover-header">
      <h3 class="tour-popover-title"></h3>
      <button type="button" class="tour-close" aria-label="Cerrar tour">&times;</button>
    </header>
    <p class="tour-popover-text"></p>
    <div class="tour-popover-footer">
      <span class="tour-counter"></span>
      <div class="tour-actions">
        <button type="button" class="button button-ghost button-compact tour-prev">Anterior</button>
        <button type="button" class="button button-ghost button-compact tour-skip">Omitir</button>
        <button type="button" class="button button-compact tour-next">Siguiente</button>
      </div>
    </div>
  `;

  const introOverlay = document.createElement("div");
  introOverlay.className = "tour-intro-overlay";
  introOverlay.innerHTML = `
    <section class="tour-intro" role="dialog" aria-modal="true" aria-labelledby="tourIntroTitle">
      <h3 id="tourIntroTitle">Tour rapido</h3>
      <p>Quieres ver una guia rapida para empezar a usar la app?</p>
      <div class="tour-intro-actions">
        <button type="button" class="button button-ghost tour-intro-skip">Ahora no</button>
        <button type="button" class="button tour-intro-start">Iniciar tour</button>
      </div>
    </section>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(popover);
  document.body.appendChild(introOverlay);

  const titleNode = popover.querySelector(".tour-popover-title");
  const textNode = popover.querySelector(".tour-popover-text");
  const counterNode = popover.querySelector(".tour-counter");
  const prevButton = popover.querySelector(".tour-prev");
  const nextButton = popover.querySelector(".tour-next");
  const skipButton = popover.querySelector(".tour-skip");
  const closeButton = popover.querySelector(".tour-close");
  const introStart = introOverlay.querySelector(".tour-intro-start");
  const introSkip = introOverlay.querySelector(".tour-intro-skip");

  const resolveSteps = () => {
    activeSteps = steps.filter((step) => document.querySelector(step.selector));
  };

  const sendState = async (url) => {
    if (!url) {
      return;
    }

    try {
      await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
      });
    } catch (_error) {
      // noop
    }
  };

  const clearHighlight = () => {
    if (highlightedNode) {
      highlightedNode.classList.remove("tour-highlight");
    }
    highlightedNode = null;
  };

  const closeTour = () => {
    clearHighlight();
    overlay.classList.remove("is-open");
    popover.classList.remove("is-open");
    document.body.classList.remove("tour-active");
  };

  const positionPopover = (target) => {
    if (!target) {
      return;
    }

    const targetRect = target.getBoundingClientRect();
    const popRect = popover.getBoundingClientRect();
    const preferredTop = targetRect.bottom + 14;
    const top = preferredTop + popRect.height > window.innerHeight - 12
      ? Math.max(12, targetRect.top - popRect.height - 14)
      : preferredTop;

    const centeredLeft = targetRect.left + targetRect.width / 2 - popRect.width / 2;
    const left = Math.min(
      Math.max(12, centeredLeft),
      Math.max(12, window.innerWidth - popRect.width - 12),
    );

    popover.style.top = `${Math.round(top)}px`;
    popover.style.left = `${Math.round(left)}px`;
  };

  const showStep = (index) => {
    if (!activeSteps.length) {
      closeTour();
      return;
    }

    const safeIndex = Math.min(Math.max(index, 0), activeSteps.length - 1);
    const step = activeSteps[safeIndex];
    const target = document.querySelector(step.selector);
    if (!target) {
      if (safeIndex < activeSteps.length - 1) {
        showStep(safeIndex + 1);
      }
      return;
    }

    currentIndex = safeIndex;
    clearHighlight();
    highlightedNode = target;
    highlightedNode.classList.add("tour-highlight");

    titleNode.textContent = step.title;
    textNode.textContent = step.text;
    counterNode.textContent = `${safeIndex + 1} / ${activeSteps.length}`;
    prevButton.disabled = safeIndex === 0;
    nextButton.textContent = safeIndex === activeSteps.length - 1 ? "Finalizar" : "Siguiente";

    target.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
    requestAnimationFrame(() => positionPopover(target));
  };

  const startTour = () => {
    resolveSteps();
    if (!activeSteps.length) {
      return;
    }

    introOverlay.classList.remove("is-open");
    overlay.classList.add("is-open");
    popover.classList.add("is-open");
    document.body.classList.add("tour-active");
    showStep(0);
  };

  const dismissTour = () => {
    closeTour();
    introOverlay.classList.remove("is-open");
    sendState(config.dismiss_url);
  };

  const completeTour = () => {
    closeTour();
    sendState(config.complete_url);
  };

  nextButton.addEventListener("click", () => {
    if (currentIndex >= activeSteps.length - 1) {
      completeTour();
      return;
    }
    showStep(currentIndex + 1);
  });

  prevButton.addEventListener("click", () => {
    if (currentIndex <= 0) {
      return;
    }
    showStep(currentIndex - 1);
  });

  skipButton.addEventListener("click", dismissTour);
  closeButton.addEventListener("click", dismissTour);
  overlay.addEventListener("click", dismissTour);

  introStart.addEventListener("click", startTour);
  introSkip.addEventListener("click", dismissTour);

  document.querySelectorAll(".js-tour-launch").forEach((button) => {
    button.addEventListener("click", startTour);
  });

  window.addEventListener("resize", () => {
    if (popover.classList.contains("is-open")) {
      positionPopover(highlightedNode);
    }
  });

  window.addEventListener("scroll", () => {
    if (popover.classList.contains("is-open")) {
      positionPopover(highlightedNode);
    }
  }, { passive: true });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    if (introOverlay.classList.contains("is-open") || popover.classList.contains("is-open")) {
      dismissTour();
    }
  });

  if (config.should_prompt) {
    window.setTimeout(() => {
      introOverlay.classList.add("is-open");
    }, 400);
  }
})();
