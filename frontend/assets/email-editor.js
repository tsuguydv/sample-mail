/** Dynamic email editor panels — only shows parts present in the email. */
window.EmailEditor = (() => {
  const BLOCK_LABELS = {
    header: "editor.block.header",
    hero: "editor.block.hero",
    hero_split: "editor.block.heroSplit",
    hero_compact: "editor.block.heroCompact",
    text: "editor.block.text",
    text_quote: "editor.block.quote",
    cta: "editor.block.cta",
    cta_banner: "editor.block.ctaBanner",
    footer: "editor.block.footer",
    image_full: "editor.block.imageFull",
    image_left: "editor.block.imageLeft",
    image_right: "editor.block.imageRight",
    gallery: "editor.block.gallery",
    article_list: "editor.block.articleList",
    video_preview: "editor.block.videoPreview",
    benefits: "editor.block.benefits",
    feature_list: "editor.block.featureList",
    icon_text: "editor.block.iconText",
    statistics: "editor.block.statistics",
    social_proof: "editor.block.socialProof",
    testimonials: "editor.block.testimonials",
    case_study: "editor.block.caseStudy",
    client_logos: "editor.block.clientLogos",
    team: "editor.block.team",
    employee: "editor.block.employee",
    product_card: "editor.block.productCard",
    product_grid: "editor.block.products",
    pricing_table: "editor.block.pricingTable",
    service_card: "editor.block.serviceCard",
    faq: "editor.block.faq",
    timeline: "editor.block.timeline",
    promo: "editor.block.promo",
    coupon: "editor.block.coupon",
    divider: "editor.block.divider",
    spacer: "editor.block.spacer",
  };

  const SLOT_LABELS = {
    subject: "result.label.subject",
    heading: "result.editor.heading",
    logo: "result.editor.logo",
    image: "result.editor.image",
    body: "result.editor.body",
    cta: "result.editor.ctaButton",
    footer: "result.editor.footer",
    page: "result.editor.pageBackground",
  };

  function label(key, fallback) {
    if (typeof t === "function") return t(key) || fallback || key;
    return fallback || key;
  }

  function blockTitle(name) {
    if (typeof blockDisplayName === "function") return blockDisplayName(name);
    const k = BLOCK_LABELS[name];
    return k ? label(k, name) : name;
  }

  function slotTitle(slot) {
    const k = SLOT_LABELS[slot];
    return k ? label(k, slot) : slot;
  }

  function inferFieldType(key, exampleVal) {
    if (typeof exampleVal === "number") return "number";
    if (typeof exampleVal === "boolean") return "checkbox";
    if (Array.isArray(exampleVal)) {
      if (exampleVal.length && typeof exampleVal[0] === "object") return "complex";
      return "lines";
    }
    if (typeof exampleVal === "object" && exampleVal !== null) return "complex";
    const k = (key || "").toLowerCase();
    if (k.includes("url") || k.includes("link") || k.includes("href")) return "url";
    if (k.includes("color")) return "color";
    if (k.includes("html") || k.includes("paragraph") || k.includes("text") || k.includes("subtitle")) return "textarea";
    return "text";
  }

  function createPanel(host, { id, title, open, onToggle }) {
    const item = document.createElement("div");
    item.className = "editor-item" + (open ? " open" : "");
    item.dataset.editorId = id;
    item.innerHTML = `
      <button type="button" class="editor-toggle">
        <span class="editor-toggle-title"></span>
        <span class="editor-arrow">▾</span>
      </button>
      <div class="editor-panel"></div>
    `;
    item.querySelector(".editor-toggle-title").textContent = title;
    const panel = item.querySelector(".editor-panel");
    const toggle = item.querySelector(".editor-toggle");
    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      item.classList.toggle("open");
      if (onToggle) onToggle(id, item.classList.contains("open"));
    });
    host.appendChild(item);
    return { item, panel, setOpen(v) { item.classList.toggle("open", !!v); }, setActive(v) { item.classList.toggle("is-active", !!v); } };
  }

  function fieldRow(labelText, inputEl) {
    const wrap = document.createElement("div");
    wrap.style.marginBottom = "8px";
    const lab = document.createElement("label");
    lab.className = "label";
    lab.textContent = labelText;
    wrap.appendChild(lab);
    wrap.appendChild(inputEl);
    return wrap;
  }

  function renderBlockFields(panel, blockMeta, ctx, onInput) {
    panel.innerHTML = "";
    if (!blockMeta || !blockMeta.parameters) {
      panel.innerHTML = `<p class="muted small">${label("editor.noFields", "No editable fields for this block.")}</p>`;
      return;
    }
    const example = blockMeta.example || {};
    Object.keys(blockMeta.parameters).forEach((key) => {
      const desc = blockMeta.parameters[key] || key;
      const ex = example[key];
      const type = inferFieldType(key, ex);
      if (type === "complex") return;

      let input;
      const val = ctx[key] !== undefined ? ctx[key] : ex;

      if (type === "lines") {
        input = document.createElement("textarea");
        input.className = "textarea";
        input.rows = 4;
        input.value = Array.isArray(val) ? val.join("\n\n") : String(val || "");
        input.addEventListener("input", () => {
          ctx[key] = String(input.value || "").split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean);
          onInput();
        });
      } else if (type === "textarea") {
        input = document.createElement("textarea");
        input.className = "textarea";
        input.rows = 4;
        input.value = String(val || "");
        input.addEventListener("input", () => { ctx[key] = input.value; onInput(); });
      } else if (type === "number") {
        input = document.createElement("input");
        input.type = "number";
        input.className = "input";
        input.value = String(val ?? "");
        input.addEventListener("input", () => { ctx[key] = Number(input.value) || 0; onInput(); });
      } else if (type === "checkbox") {
        input = document.createElement("input");
        input.type = "checkbox";
        input.checked = !!val;
        input.addEventListener("change", () => { ctx[key] = input.checked; onInput(); });
      } else {
        input = document.createElement("input");
        input.type = type === "url" ? "url" : type === "color" ? "color" : "text";
        input.className = "input";
        input.value = String(val || "");
        input.addEventListener("input", () => { ctx[key] = input.value; onInput(); });
      }
      panel.appendChild(fieldRow(desc, input));
    });
  }

  function buildModularEditor(host, { generation, blocksCatalog, onChange, onFocusBlock }) {
    host.innerHTML = "";
    const panels = [];
    const catalog = {};
    (blocksCatalog || []).forEach((b) => { catalog[b.name] = b; });

    const subjectPanel = createPanel(host, {
      id: "subject",
      title: slotTitle("subject"),
      open: true,
      onToggle: (id) => { if (onFocusBlock) onFocusBlock({ type: "subject" }); },
    });
    const subjectInput = document.createElement("input");
    subjectInput.className = "input";
    subjectInput.type = "text";
    subjectInput.value = generation.subject || "";
    subjectInput.addEventListener("input", () => {
      generation.subject = subjectInput.value.trim();
      onChange();
    });
    subjectPanel.panel.appendChild(fieldRow(slotTitle("subject"), subjectInput));
    panels.push({ id: "subject", ui: subjectPanel });

    const layout = generation.blockLayout || [];
    layout.forEach((block, index) => {
      if (!block.context || typeof block.context !== "object") block.context = {};
      const meta = catalog[block.name] || { parameters: {}, example: {} };
      const ui = createPanel(host, {
        id: `block-${index}`,
        title: `${index + 1}. ${blockTitle(block.name)}`,
        open: index === 0,
        onToggle: () => { if (onFocusBlock) onFocusBlock({ type: "block", blockIndex: index }); },
      });
      renderBlockFields(ui.panel, meta, block.context, onChange);
      panels.push({ id: `block-${index}`, ui, blockIndex: index });
    });

    if (generation.imageOptions && generation.imageOptions.length) {
      const imgPanel = createPanel(host, {
        id: "ai-image",
        title: label("editor.aiImage", "AI image variant"),
        open: false,
        onToggle: () => {},
      });
      const sel = document.createElement("select");
      sel.className = "select";
      generation.imageOptions.forEach((opt, i) => {
        const o = document.createElement("option");
        o.value = String(i);
        o.textContent = `${label("editor.variant", "Variant")} ${i + 1}`;
        sel.appendChild(o);
      });
      sel.addEventListener("change", () => {
        generation._imageIndex = Number(sel.value) || 0;
        onChange();
      });
      imgPanel.panel.appendChild(fieldRow(label("editor.imageVariant", "Image"), sel));
      panels.push({ id: "ai-image", ui: imgPanel });
    }

    function focusTarget(target) {
      panels.forEach((p) => p.ui.setActive(false));
      if (!target) return;
      if (target.type === "subject") {
        subjectPanel.setActive(true);
        subjectPanel.setOpen(true);
        return;
      }
      if (target.type === "block") {
        const p = panels.find((x) => x.blockIndex === target.blockIndex);
        if (p) { p.ui.setActive(true); p.ui.setOpen(true); }
      }
    }

    return { panels, focusTarget };
  }

  function buildClassicEditor(host, { generation, visibleSlots, styleState, onChange, onFocusSlot }) {
    host.innerHTML = "";
    const panels = [];
    const slots = visibleSlots && visibleSlots.length ? visibleSlots : ["heading", "body", "cta", "footer"];

    function addSubject() {
      const ui = createPanel(host, { id: "subject", title: slotTitle("subject"), open: true, onToggle: () => onFocusSlot && onFocusSlot("subject") });
      const input = document.createElement("input");
      input.className = "input";
      input.value = generation.subject || "";
      input.addEventListener("input", () => { generation.subject = input.value.trim(); onChange(); });
      ui.panel.appendChild(fieldRow(slotTitle("subject"), input));
      panels.push({ slot: "subject", ui });
    }

    function addBody() {
      if (!slots.includes("body")) return;
      const ui = createPanel(host, { id: "body", title: slotTitle("body"), open: true, onToggle: () => onFocusSlot && onFocusSlot("body") });
      (generation.textOptions || [{ html: "" }]).forEach((opt, i) => {
        const ta = document.createElement("textarea");
        ta.className = "textarea";
        ta.rows = 5;
        ta.value = opt.html || "";
        ta.addEventListener("input", () => { opt.html = ta.value; onChange(); });
        ui.panel.appendChild(fieldRow(`${slotTitle("body")} ${i + 1}`, ta));
      });
      panels.push({ slot: "body", ui });
    }

    function addImage() {
      if (!slots.includes("image") || !(generation.imageOptions || []).length) return;
      const ui = createPanel(host, { id: "image", title: slotTitle("image"), open: false, onToggle: () => onFocusSlot && onFocusSlot("image") });
      const sel = document.createElement("select");
      sel.className = "select";
      generation.imageOptions.forEach((_, i) => {
        const o = document.createElement("option");
        o.value = String(i);
        o.textContent = `${label("editor.variant", "Variant")} ${i + 1}`;
        sel.appendChild(o);
      });
      sel.addEventListener("change", () => { generation._imageIndex = Number(sel.value) || 0; onChange(); });
      ui.panel.appendChild(fieldRow(label("editor.imageVariant", "Image"), sel));
      panels.push({ slot: "image", ui });
    }

    function addCta() {
      if (!slots.includes("cta") || !(generation.ctaOptions || []).length) return;
      const ui = createPanel(host, { id: "cta", title: slotTitle("cta"), open: false, onToggle: () => onFocusSlot && onFocusSlot("cta") });
      const idx = generation._ctaIndex || 0;
      const opt = generation.ctaOptions[idx] || {};
      const labelIn = document.createElement("input");
      labelIn.className = "input";
      labelIn.value = opt.label || "";
      labelIn.addEventListener("input", () => { opt.label = labelIn.value; onChange(); });
      const linkIn = document.createElement("input");
      linkIn.className = "input";
      linkIn.type = "url";
      linkIn.value = opt.href || "";
      linkIn.addEventListener("input", () => { opt.href = linkIn.value; onChange(); });
      ui.panel.appendChild(fieldRow(label("editor.ctaLabel", "Button text"), labelIn));
      ui.panel.appendChild(fieldRow(label("editor.ctaLink", "Link URL"), linkIn));
      panels.push({ slot: "cta", ui });
    }

    function addStyleSlot(slot) {
      if (!slots.includes(slot)) return;
      const ui = createPanel(host, { id: slot, title: slotTitle(slot), open: false, onToggle: () => onFocusSlot && onFocusSlot(slot) });
      if (!styleState[slot]) styleState[slot] = {};
      const st = styleState[slot];
      const align = document.createElement("select");
      align.className = "select";
      ["", "left", "center", "right"].forEach((v) => {
        const o = document.createElement("option");
        o.value = v;
        o.textContent = v || label("editor.default", "Default");
        align.appendChild(o);
      });
      align.value = st.align || "";
      align.addEventListener("change", () => { st.align = align.value; onChange(); });
      ui.panel.appendChild(fieldRow(label("editor.align", "Align"), align));
      panels.push({ slot, ui });
    }

    addSubject();
    if (slots.includes("heading")) addStyleSlot("heading");
    addImage();
    addBody();
    addCta();
    if (slots.includes("footer")) addStyleSlot("footer");
    if (slots.includes("page")) addStyleSlot("page");

    function focusSlot(slot) {
      panels.forEach((p) => p.ui.setActive(false));
      const p = panels.find((x) => x.slot === slot);
      if (p) { p.ui.setActive(true); p.ui.setOpen(true); }
    }

    return { panels, focusSlot };
  }

  return {
    blockTitle,
    slotTitle,
    buildModularEditor,
    buildClassicEditor,
  };
})();
