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

  const replacePartialContent = (html) => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const nextPagination = doc.getElementById(PAGINATION_ID);
    const nextTable = doc.getElementById(TABLE_ID);
    if (!nextPagination || !nextTable) {
      return false;
    }

    const currentPagination = document.getElementById(PAGINATION_ID);
    const currentTable = document.getElementById(TABLE_ID);
    if (!currentPagination || !currentTable) {
      return false;
    }

    currentPagination.replaceWith(nextPagination);
    currentTable.replaceWith(nextTable);
    return true;
  };

  const toAbsoluteUrl = (targetUrl) => new URL(targetUrl, window.location.origin);

  const fetchAndReplace = async (targetUrl, options = {}) => {
    const { historyMode = "replace", signal } = options;
    const requestUrl = toAbsoluteUrl(targetUrl);
    requestUrl.searchParams.set("partial", "1");
    const pageUrl = toAbsoluteUrl(targetUrl);

    const paginationContainer = document.getElementById(PAGINATION_ID);
    const tableContainer = document.getElementById(TABLE_ID);
    setLoadingState(paginationContainer, true);
    setLoadingState(tableContainer, true);

    try {
      const response = await fetch(requestUrl.toString(), {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
        signal,
      });

      if (!response.ok) {
        throw new Error("No se pudo cargar la pagina");
      }

      const html = await response.text();
      const replaced = replacePartialContent(html);
      if (!replaced) {
        throw new Error("Respuesta parcial invalida");
      }

      if (historyMode === "push") {
        history.pushState(null, "", pageUrl.toString());
      } else if (historyMode === "replace") {
        history.replaceState(null, "", pageUrl.toString());
      }

      document.dispatchEvent(new CustomEvent("table:updated"));
      document.dispatchEvent(new CustomEvent("pagination:updated"));
      return true;
    } catch (error) {
      if (error?.name === "AbortError") {
        return false;
      }
      return false;
    } finally {
      const currentPagination = document.getElementById(PAGINATION_ID);
      const currentTable = document.getElementById(TABLE_ID);
      setLoadingState(currentPagination, false);
      setLoadingState(currentTable, false);
    }
  };

  const createTableSearch = (config) => {
    const {
      searchInput,
      queryParam = "q",
      debounceMs = 700,
      minChars = 2,
      applyLocalFilter,
      collectParams,
      onTableUpdated,
    } = config;

    if (!searchInput) {
      return null;
    }

    let debounceTimer = null;
    let requestSeq = 0;
    let latestApplied = 0;
    let activeController = null;

    const getParams = () => {
      const params = new URLSearchParams(window.location.search);
      const queryValue = searchInput.value.trim();

      if (queryValue) {
        params.set(queryParam, queryValue);
      } else {
        params.delete(queryParam);
      }

      if (typeof collectParams === "function") {
        collectParams(params);
      }
      params.delete("page");
      return params;
    };

    const remoteUpdate = async (historyMode) => {
      const queryValue = searchInput.value.trim();
      if (queryValue.length > 0 && queryValue.length < minChars) {
        return;
      }

      const params = getParams();
      const queryString = params.toString();
      const target = queryString
        ? `${window.location.pathname}?${queryString}`
        : window.location.pathname;

      if (activeController) {
        activeController.abort();
      }
      activeController = new AbortController();
      requestSeq += 1;
      const seq = requestSeq;

      const ok = await fetchAndReplace(target, {
        historyMode,
        signal: activeController.signal,
      });
      if (!ok || seq < latestApplied) {
        return;
      }
      latestApplied = seq;
      if (typeof onTableUpdated === "function") {
        onTableUpdated();
      }
    };

    const scheduleRemoteUpdate = (historyMode = "replace") => {
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        remoteUpdate(historyMode);
      }, debounceMs);
    };

    const applyLocal = () => {
      if (typeof applyLocalFilter === "function") {
        applyLocalFilter(searchInput.value.trim());
      }
    };

    const onInput = () => {
      applyLocal();
      scheduleRemoteUpdate("replace");
    };

    searchInput.addEventListener("input", onInput);

    return {
      refresh: (historyMode = "replace") => remoteUpdate(historyMode),
      applyLocal,
      destroy: () => {
        window.clearTimeout(debounceTimer);
        if (activeController) {
          activeController.abort();
        }
        searchInput.removeEventListener("input", onInput);
      },
    };
  };

  window.TableSearch = {
    fetchAndReplace,
    createTableSearch,
  };
})();
