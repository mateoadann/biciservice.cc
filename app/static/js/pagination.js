(() => {
  const PAGINATION_ID = "pagination-content";
  const TABLE_ID = "table-content";

  const setLoadingState = (container, isLoading) => {
    if (!container) {
      return;
    }
    container.style.opacity = isLoading ? "0.5" : "";
    container.style.pointerEvents = isLoading ? "none" : "";
  };

  document.addEventListener("click", async (event) => {
    if (event.defaultPrevented || event.button !== 0) {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    const button = event.target.closest("a.pagination-btn");
    if (!button) {
      return;
    }

    const paginationContainer = document.getElementById(PAGINATION_ID);
    const tableContainer = document.getElementById(TABLE_ID);
    if (!paginationContainer || !tableContainer) {
      return;
    }

    event.preventDefault();

    const requestUrl = new URL(button.href, window.location.origin);
    requestUrl.searchParams.set("partial", "1");
    const pageUrl = new URL(button.href, window.location.origin);

    setLoadingState(paginationContainer, true);
    setLoadingState(tableContainer, true);

    try {
      const response = await fetch(requestUrl.toString(), {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error("No se pudo cargar la pagina");
      }

      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const nextPagination = doc.getElementById(PAGINATION_ID);
      const nextTable = doc.getElementById(TABLE_ID);

      if (!nextPagination || !nextTable) {
        window.location.href = pageUrl.toString();
        return;
      }

      paginationContainer.replaceWith(nextPagination);
      tableContainer.replaceWith(nextTable);
      history.pushState(null, "", pageUrl.toString());
      document.dispatchEvent(new CustomEvent("pagination:updated"));
    } catch (error) {
      window.location.href = pageUrl.toString();
    } finally {
      const currentPagination = document.getElementById(PAGINATION_ID);
      const currentTable = document.getElementById(TABLE_ID);
      setLoadingState(currentPagination, false);
      setLoadingState(currentTable, false);
    }
  });

  window.addEventListener("popstate", () => {
    if (document.getElementById(PAGINATION_ID) || document.getElementById(TABLE_ID)) {
      window.location.reload();
    }
  });
})();
