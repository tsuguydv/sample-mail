
// UI helpers: swipe module + modal

function createSwipeModule({ items, index, onIndexChange, renderItem, ariaLabel, persistBeforeIndexChange, swipeIgnoreSelector }){
  if(!items || items.length === 0) return document.createElement("div");

  const root = document.createElement("div");
  root.className = "swipe";
  root.setAttribute("aria-label", ariaLabel || "");

  const stage = document.createElement("div");
  stage.className = "swipe-stage";
  stage.style.userSelect = "none";

  const nav = document.createElement("div");
  nav.className = "swipe-nav";

  const btnL = document.createElement("button");
  btnL.type = "button";
  btnL.className = "swipe-btn left";
  btnL.innerHTML = "‹";
  btnL.addEventListener("click", () => go(-1));

  const btnR = document.createElement("button");
  btnR.type = "button";
  btnR.className = "swipe-btn right";
  btnR.innerHTML = "›";
  btnR.addEventListener("click", () => go(1));

  nav.append(btnL, btnR);
  root.append(stage, nav);

  let currentIndex = index || 0;

  function disableNativeDrag(container){
    // Safari/macOS can start native drag for images/text, which makes content
    // appear to "follow the cursor". Disable native drag behavior in swipe area.
    container.querySelectorAll("img, a").forEach((el) => {
      el.setAttribute("draggable", "false");
    });
  }

  function normalize(i){
    const n = items.length;
    return ((i % n) + n) % n;
  }
  function go(dir){
    if(items.length <= 1) return;
    if(typeof persistBeforeIndexChange === "function"){
      persistBeforeIndexChange(currentIndex);
    }
    currentIndex = normalize(currentIndex + dir);
    onIndexChange(currentIndex);
    render();
  }

  // pointer swipe
  let startX = 0;
  let startTime = 0;
  let dragging = false;

  stage.addEventListener("dragstart", (e) => {
    e.preventDefault();
  });

  stage.addEventListener("pointerdown", (e) => {
    if(swipeIgnoreSelector && e.target.closest(swipeIgnoreSelector)){
      return;
    }
    dragging = true;
    stage.setPointerCapture(e.pointerId);
    startX = e.clientX;
    startTime = Date.now();
  });
  stage.addEventListener("pointermove", (e) => {
    if(!dragging) return;
    // no visual drag; we just track dx
  });
  stage.addEventListener("pointerup", (e) => {
    if(!dragging) return;
    dragging = false;
    const dx = e.clientX - startX;
    const elapsed = Date.now() - startTime;
    const velocity = Math.abs(dx) / Math.max(elapsed, 1);
    const SWIPE_THRESHOLD = 50;
    const MIN_VELOCITY = 0.2;
    if(Math.abs(dx) > SWIPE_THRESHOLD || velocity > MIN_VELOCITY){
      if(dx > 0) go(-1);
      else if(dx < 0) go(1);
    }
  });

  function render(){
    stage.innerHTML = "";
    stage.append(renderItem(items[currentIndex]));
    disableNativeDrag(stage);
    btnL.disabled = items.length <= 1;
    btnR.disabled = items.length <= 1;
  }

  render();
  return root;
}

function createEditModal({ onSubmit }){
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.setAttribute("role","dialog");
  backdrop.setAttribute("aria-modal","true");

  const modal = document.createElement("div");
  modal.className = "modal";

  modal.innerHTML = `
    <div class="card-pad">
      <h2 class="h3" id="edit-modal-title" data-i18n="modal.edit.title">Запросить правки</h2>
      <p class="p small" data-i18n="modal.edit.subtitle">Заполните только те поля, которые нужно изменить. Пустое поле — модуль не меняется.</p>
      <div class="spacer-4"></div>

      <form id="edit-form" class="grid" style="gap:14px;">
        <div>
          <label class="label" data-i18n="modal.edit.label.image">Правки к картинке</label>
          <textarea class="textarea" rows="2" name="imageFeedback"></textarea>
        </div>
        <div>
          <label class="label" data-i18n="modal.edit.label.text">Правки к тексту письма</label>
          <textarea class="textarea" rows="3" name="textFeedback"></textarea>
        </div>
        <div>
          <label class="label" data-i18n="modal.edit.label.cta">Правки к кнопке</label>
          <textarea class="textarea" rows="2" name="ctaFeedback"></textarea>
        </div>

        <div class="row" style="gap:12px; padding-top:4px;">
          <button class="btn btn-primary col" type="submit" id="edit-submit" data-i18n="modal.edit.submit">Отправить</button>
          <button class="btn btn-outline col" type="button" id="edit-cancel" data-i18n="modal.edit.cancel">Отмена</button>
        </div>
      </form>
    </div>
  `;
  // Apply translations to the newly created modal content
  if(typeof applyTranslations === "function") applyTranslations();
  backdrop.appendChild(modal);

  let open = false;
  let previousActive = null;

  function setOpen(v){
    open = !!v;
    backdrop.classList.toggle("open", open);
    if(open){
      previousActive = document.activeElement;
      const first = modal.querySelector("textarea, input, select, button");
      first && first.focus();
      document.body.style.overflow = "hidden";
    }else{
      document.body.style.overflow = "";
      if(previousActive && previousActive.focus) previousActive.focus();
      previousActive = null;
      // reset fields
      const form = modal.querySelector("#edit-form");
      form && form.reset();
    }
  }

  backdrop.addEventListener("click", (e) => {
    if(e.target === backdrop) setOpen(false);
  });
  document.addEventListener("keydown", (e) => {
    if(!open) return;
    if(e.key === "Escape") setOpen(false);
  });

  const form = modal.querySelector("#edit-form");
  const btnCancel = modal.querySelector("#edit-cancel");
  const btnSubmit = modal.querySelector("#edit-submit");

  btnCancel.addEventListener("click", () => setOpen(false));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btnSubmit.disabled = true;
    const fd = new FormData(form);
    const data = {
      imageFeedback: (fd.get("imageFeedback") || "").toString(),
      textFeedback: (fd.get("textFeedback") || "").toString(),
      ctaFeedback: (fd.get("ctaFeedback") || "").toString(),
    };
    try{
      await onSubmit(data);
      setOpen(false);
    }finally{
      btnSubmit.disabled = false;
    }
  });

  return { el: backdrop, open: () => setOpen(true), close: () => setOpen(false) };
}
