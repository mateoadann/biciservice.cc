(() => {
  const overlay = document.getElementById("detailDrawer");
  if (!overlay) return;

  const titleEl = overlay.querySelector(".drawer-title");
  const bodyEl = overlay.querySelector(".drawer-body");
  const footerEl = overlay.querySelector(".drawer-footer");
  const closeBtn = overlay.querySelector(".modal-close");

  const close = () => {
    overlay.classList.remove("is-open");
    overlay.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };

  const open = (title, bodyContent, footerContent) => {
    titleEl.textContent = title;
    bodyEl.replaceChildren();
    footerEl.replaceChildren();
    if (bodyContent) bodyEl.appendChild(bodyContent);
    if (footerContent) footerEl.appendChild(footerContent);
    overlay.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  };

  closeBtn?.addEventListener("click", close);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.classList.contains("is-open")) close();
  });

  document.addEventListener("click", (e) => {
    if (e.target.closest(".js-confirm") || e.target.closest("a.button") || e.target.closest("button")) return;
    const card = e.target.closest("[data-drawer]");
    if (!card) return;
    const templateId = card.dataset.drawer;
    const template = document.getElementById(templateId);
    if (!template) return;
    const content = template.content.cloneNode(true);
    const drawerTitle = card.dataset.drawerTitle || "Detalle";
    const bodyDiv = content.querySelector(".drawer-detail-body");
    const footerDiv = content.querySelector(".drawer-detail-footer");
    open(drawerTitle, bodyDiv, footerDiv);
  });
})();
