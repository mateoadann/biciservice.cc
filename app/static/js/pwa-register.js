(() => {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  const isSecureContextForSw =
    window.location.protocol === "https:" ||
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

  if (!isSecureContextForSw) {
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((error) => {
      console.warn("No se pudo registrar el service worker", error);
    });
  });
})();
