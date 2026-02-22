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

  const clearServiceWorkerCaches = async () => {
    if (!("caches" in window)) {
      return;
    }
    const keys = await caches.keys();
    const targets = keys.filter((key) => key.startsWith("service-bicycle-static-"));
    await Promise.all(targets.map((key) => caches.delete(key)));
  };

  const unregisterAllServiceWorkers = async () => {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
  };

  window.addEventListener("load", () => {
    const swEnabled = Boolean(window.__SERVICE_WORKER_ENABLED__);
    const assetVersion = window.__ASSET_VERSION__ || "dev";
    if (!swEnabled) {
      unregisterAllServiceWorkers()
        .then(clearServiceWorkerCaches)
        .catch((error) => {
          console.warn("No se pudo limpiar el service worker en desarrollo", error);
        });
      return;
    }
    const swUrl = `/sw.js?v=${encodeURIComponent(assetVersion)}`;
    navigator.serviceWorker.register(swUrl, { scope: "/" }).catch((error) => {
      console.warn("No se pudo registrar el service worker", error);
    });
  });
})();
