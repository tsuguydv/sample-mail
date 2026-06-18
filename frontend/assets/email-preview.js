/** Email preview viewport — no scale hack; scroll + auto height. */
window.EmailPreview = (() => {
  function parseHtml(html) {
    return new DOMParser().parseFromString(html || "", "text/html");
  }

  function serializeDoc(doc) {
    return "<!doctype html>\n" + doc.documentElement.outerHTML;
  }

  function injectHelperStyles(doc) {
    const style = doc.createElement("style");
    style.textContent = `
      html, body { margin: 0; padding: 0; overflow-x: hidden !important; }
      body { min-height: 100%; }
      [data-edit-slot], [data-edit-block] { transition: outline-color .12s ease; cursor: pointer; }
      [data-edit-slot].ep-active, [data-edit-block].ep-active {
        outline: 2px solid #4f46e5 !important; outline-offset: 2px;
      }
      [data-edit-slot].ep-hover, [data-edit-block].ep-hover {
        outline: 2px dashed #818cf8 !important; outline-offset: 2px;
      }
    `;
    doc.head.appendChild(style);
  }

  function resizeFrame(frame) {
    if (!frame || !frame.contentDocument) return;
    const doc = frame.contentDocument;
    const html = doc.documentElement;
    const body = doc.body;
    if (!html || !body) return;
    body.style.margin = "0";
    body.style.overflowX = "hidden";
    html.style.overflowX = "hidden";
    const h = Math.max(
      body.scrollHeight || 0,
      html.scrollHeight || 0,
      body.offsetHeight || 0,
      400
    );
    frame.style.height = `${h + 24}px`;
  }

  function bindHighlights(frame, onTarget) {
    const doc = frame.contentDocument;
    if (!doc) return () => {};
    const cleanups = [];
    const nodes = doc.querySelectorAll("[data-edit-slot], [data-edit-block]");
    nodes.forEach((el) => {
      const slot = el.getAttribute("data-edit-slot");
      const block = el.getAttribute("data-edit-block");
      const enter = () => el.classList.add("ep-hover");
      const leave = () => el.classList.remove("ep-hover");
      const click = (e) => {
        e.preventDefault();
        if (onTarget) onTarget({ slot, blockIndex: block != null ? Number(block) : null, el });
      };
      el.addEventListener("mouseenter", enter);
      el.addEventListener("mouseleave", leave);
      el.addEventListener("click", click);
      cleanups.push(() => {
        el.removeEventListener("mouseenter", enter);
        el.removeEventListener("mouseleave", leave);
        el.removeEventListener("click", click);
      });
    });
    return () => cleanups.forEach((fn) => fn());
  }

  function setActiveTarget(frame, target) {
    const doc = frame && frame.contentDocument;
    if (!doc) return;
    doc.querySelectorAll("[data-edit-slot], [data-edit-block]").forEach((el) => {
      el.classList.remove("ep-active");
    });
    if (!target) return;
    if (target.slot) {
      const el = doc.querySelector(`[data-edit-slot="${target.slot}"]`);
      if (el) {
        el.classList.add("ep-active");
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
    if (target.blockIndex != null && !Number.isNaN(target.blockIndex)) {
      const el = doc.querySelector(`[data-edit-block="${target.blockIndex}"]`);
      if (el) {
        el.classList.add("ep-active");
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }

  function wrapModularBlocks(html) {
    const doc = parseHtml(html);
    const container = doc.querySelector(".email-container") || doc.querySelector("table.email-container");
    if (!container) return html;
    let idx = 0;
    container.querySelectorAll(":scope > tbody > tr, :scope > tr").forEach((tr) => {
      tr.setAttribute("data-edit-block", String(idx));
      idx += 1;
    });
    return serializeDoc(doc);
  }

  function detectClassicSlots(html) {
    const doc = parseHtml(html);
    const slots = new Set();
    doc.querySelectorAll("[data-edit-slot]").forEach((el) => {
      const s = el.getAttribute("data-edit-slot");
      if (s) slots.add(s);
    });
    return [...slots];
  }

  return {
    parseHtml,
    serializeDoc,
    injectHelperStyles,
    resizeFrame,
    bindHighlights,
    setActiveTarget,
    wrapModularBlocks,
    detectClassicSlots,
  };
})();
