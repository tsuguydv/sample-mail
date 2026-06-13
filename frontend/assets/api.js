// Real API layer (Python backend)
// Same interface as the original mock API.
// Backend endpoints:
//   POST   /api/login
//   GET    /api/company
//   PUT    /api/company
//   POST   /api/logo
//   GET    /api/templates
//   POST   /api/generate
//   POST   /api/generate/start
//   GET    /api/generate/jobs
//   GET    /api/generate/job/{jobId}/result  (when job status is done)
//   POST   /api/refine

const API = (() => {
  const TOKEN_KEY = "taskflock_token";

  function getToken(){
    return localStorage.getItem(TOKEN_KEY);
  }

  function redirectToLoginOnExpiredSession(){
    const page = (location.pathname.split("/").pop() || "").toLowerCase();
    if(page === "login.html" || page === "register.html" || page === "index.html" || page === ""){
      return;
    }
    try{
      localStorage.removeItem(TOKEN_KEY);
    }catch{}
    window.location.href = "login.html";
  }

  async function request(path, { method="GET", headers={}, body=null, auth=true } = {}){
    const h = { ...headers };
    if(auth){
      const t = getToken();
      if(t) h["Authorization"] = "Bearer " + t;
    }
    const res = await fetch(path, {
      method,
      headers: h,
      body,
      cache: "no-store",
    });

    if(res.status === 401 && auth){
      redirectToLoginOnExpiredSession();
      throw new Error("Session expired");
    }

    // FastAPI returns JSON errors like {"detail": "..."}
    if(!res.ok){
      let msg = `HTTP ${res.status}`;
      try{
        const data = await res.json();
        if(data && data.detail){
          if(Array.isArray(data.detail)){
            const first = data.detail[0];
            if(first && first.loc && Array.isArray(first.loc) && first.loc.includes("email")){
              msg = "Некорректный email";
            }else if(first && typeof first.msg === "string"){
              msg = first.msg;
            }
          }else if(typeof data.detail === "string"){
            msg = data.detail;
          }
        }
      }catch{
        try{ msg = await res.text(); }catch{}
      }
      throw new Error(msg);
    }

    // some endpoints may return empty
    const ct = res.headers.get("content-type") || "";
    if(ct.includes("application/json")){
      return await res.json();
    }
    return await res.text();
  }

  async function login(email, password){
    const data = await request("/api/login", {
      method: "POST",
      auth: false,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    // data: {token, user}
    return data;
  }

  async function register(email, password, legalConsentAccepted=false){
    const data = await request("/api/register", {
      method: "POST",
      auth: false,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, legalConsentAccepted })
    });
    return data;
  }

  async function verifyEmail(token){
    const q = `?token=${encodeURIComponent(token)}`;
    return await request(`/api/auth/verify-email${q}`, { method: "GET", auth: false });
  }

  async function resendVerification(email){
    return await request("/api/auth/resend-verification", {
      method: "POST",
      auth: false,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  }

  async function getCompany(){
    return await request("/api/company", { method: "GET" });
  }

  async function updateCompany(data){
    return await request("/api/company", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
  }

  async function verifyCompanySender(){
    return await request("/api/company/verify-sender", { method: "POST" });
  }

  async function uploadLogo(file){
    const fd = new FormData();
    fd.append("file", file);
    return await request("/api/logo", { method: "POST", body: fd, headers: {}, auth: true });
  }

  async function uploadAvatar(file){
    const fd = new FormData();
    fd.append("file", file);
    return await request("/api/avatar", { method: "POST", body: fd, headers: {}, auth: true });
  }

  async function getBlocks(){
    const lang = (typeof Store !== "undefined" && Store.getLanguage) ? Store.getLanguage() : "ru";
    return await request(`/api/blocks?lang=${encodeURIComponent(lang)}`, { method: "GET" });
  }

  async function renderTemplatePreview(payload){
    const data = await request("/api/templates/render-preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.html || "";
  }

  async function getTemplates(){
    return await request("/api/templates", { method: "GET" });
  }


  async function generate(params){
    return await request("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params)
    });
  }

  async function startGenerate(params){
    return await request("/api/generate/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
  }

  async function getGenerateJobs(limit){
    const q = limit != null && String(limit).trim() !== "" ? `?limit=${encodeURIComponent(String(limit))}` : "";
    return await request(`/api/generate/jobs${q}`, { method: "GET" });
  }

  async function getGenerateJobResult(jobId){
    return await request(`/api/generate/job/${encodeURIComponent(jobId)}/result`, { method: "GET" });
  }

  async function retryGenerateJob(jobId){
    return await request(`/api/generate/job/${encodeURIComponent(jobId)}/retry`, { method: "POST" });
  }

  async function deleteGenerateJob(jobId){
    return await request(`/api/generate/job/${encodeURIComponent(jobId)}`, { method: "DELETE" });
  }

  async function refine(params){
    return await request("/api/refine", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params)
    });
  }

  async function putGenerationSession(sessionId, generation){
    return await request(`/api/generation-session/${encodeURIComponent(sessionId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(generation),
    });
  }

  async function getGeneratedEmails(){
    return await request("/api/generated-emails", { method: "GET" });
  }

  async function getGeneratedEmail(id){
    return await request(`/api/generated-emails/${id}`, { method: "GET" });
  }

  async function updateGeneratedEmail(id, data){
    return await request(`/api/generated-emails/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  }

  async function createGeneratedEmail(data){
    return await request("/api/generated-emails", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  }

  async function deleteGeneratedEmail(id){
    return await request(`/api/generated-emails/${id}`, { method: "DELETE" });
  }

  async function getAccount(){
    return await request("/api/account", { method: "GET" });
  }

  async function updateAccount(data){
    return await request("/api/account", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  }

  async function updatePassword(currentPassword, newPassword){
    return await request("/api/account/password", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currentPassword, newPassword }),
    });
  }

  async function getSessions(){
    return await request("/api/account/sessions", { method: "GET" });
  }

  async function revokeSession(id){
    return await request(`/api/account/sessions/${id}`, { method: "DELETE" });
  }

  async function logoutCurrentSession(){
    return await request("/api/account/sessions/current", { method: "DELETE" });
  }

  async function deleteAccount(){
    return await request("/api/account", { method: "DELETE" });
  }

  async function exportAccountData(){
    return await request("/api/account/export", { method: "GET" });
  }

  async function getBillingStatus(){
    return await request("/api/billing/status", { method: "GET" });
  }

  async function createPaypalSubscription(body){
    return await request("/api/billing/paypal/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
  }

  async function getGenerationQuote(templateId){
    const q = encodeURIComponent(templateId || "t1");
    return await request(`/api/billing/generation-quote?templateId=${q}`, { method: "GET" });
  }

  async function createPaypalTokenOrder(body){
    return await request("/api/billing/paypal/buy-tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
  }

  async function capturePaypalOrder(body){
    return await request("/api/billing/paypal/capture-order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
  }

  async function listRefundRequests(){
    return await request("/api/billing/refund-requests", { method: "GET" });
  }

  async function createRefundRequest(data){
    return await request("/api/billing/refund-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {}),
    });
  }

  // Export final email by calling the backend template renderer
  async function exportEmail(sessionId, imageIndex, textIndex, ctaIndex, generation){
    if(!sessionId){
      throw new Error("Session ID is required for export");
    }

    const token = getToken();
    const response = await fetch("/api/export", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({
        session_id: sessionId,
        image_index: imageIndex || 0,
        text_index: textIndex || 0,
        cta_index: ctaIndex || 0,
        blockLayout: generation && generation.blockLayout ? generation.blockLayout : undefined,
      }),
    });

    if(response.status === 401){
      redirectToLoginOnExpiredSession();
      throw new Error("Session expired");
    }

    if(!response.ok){
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "Failed to export email");
    }

    const data = await response.json();
    return new Blob([data.html], { type: "text/html" });
  }

  async function getUserTemplates(){
    return await request("/api/user-templates", { method: "GET" });
  }

  async function getUserTemplate(id){
    return await request(`/api/user-templates/${encodeURIComponent(id)}`, { method: "GET" });
  }

  async function createUserTemplate(data){
    return await request("/api/user-templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {}),
    });
  }

  async function updateUserTemplate(id, data){
    return await request(`/api/user-templates/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {}),
    });
  }

  async function deleteUserTemplate(id){
    return await request(`/api/user-templates/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  return {
    login, register, verifyEmail, resendVerification,
    getCompany, updateCompany, uploadLogo, uploadAvatar,
    verifyCompanySender,
    getTemplates, getBlocks, renderTemplatePreview,
    generate, startGenerate, getGenerateJobs, getGenerateJobResult, retryGenerateJob, deleteGenerateJob, refine, putGenerationSession, exportEmail,
    getGeneratedEmails, getGeneratedEmail, updateGeneratedEmail, createGeneratedEmail, deleteGeneratedEmail,
    getAccount, updateAccount, updatePassword, getSessions, revokeSession, logoutCurrentSession, deleteAccount, exportAccountData,
    getBillingStatus, createPaypalSubscription, getGenerationQuote,
    createPaypalTokenOrder, capturePaypalOrder,
    getUserTemplates, getUserTemplate, createUserTemplate, updateUserTemplate, deleteUserTemplate,
    listRefundRequests, createRefundRequest,
  };
})();
