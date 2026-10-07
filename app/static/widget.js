/* support-bot widget. Drop into any page:
     <script src="https://your-host/static/widget.js" data-endpoint="https://your-host" data-title="Support"></script>
   No framework, no dependencies. Styles are scoped under .sb-root. */
(function () {
  const script = document.currentScript;
  const endpoint = (script.dataset.endpoint || "").replace(/\/$/, "");
  const title = script.dataset.title || "Support assistant";
  const greeting = script.dataset.greeting || "Hello! Ask me about prices, opening hours or our services. I answer from our own documents and show you where I looked.";
  let sessionId = sessionStorage.getItem("sb-session") || null;

  const css = `
  .sb-root{--sb-ink:#10222C;--sb-canvas:#0E2B38;--sb-paper:#F1F3F0;--sb-mint:#7FE3D2;--sb-marker:#FFD23F;--sb-muted:#5B6B72;
    font-family:Lato,"Segoe UI",system-ui,sans-serif;position:fixed;right:24px;bottom:24px;z-index:99999}
  .sb-root *{box-sizing:border-box}
  .sb-fab{width:60px;height:60px;border-radius:50%;background:var(--sb-canvas);color:#fff;border:0;cursor:pointer;
    box-shadow:0 14px 30px -12px rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;font-size:24px}
  .sb-fab:hover{transform:translateY(-1px)}
  .sb-panel{position:absolute;right:0;bottom:76px;width:380px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 120px);
    background:var(--sb-paper);color:var(--sb-ink);border-radius:16px;box-shadow:0 30px 60px -28px rgba(0,0,0,.7);
    display:none;flex-direction:column;overflow:hidden}
  .sb-root.open .sb-panel{display:flex}
  .sb-head{height:54px;display:flex;align-items:center;gap:10px;padding:0 16px;border-bottom:1px solid #D7DEDA;font-size:15px}
  .sb-head b{font-weight:900}.sb-head .sb-dot{width:9px;height:9px;border-radius:50%;background:#2DB77C}
  .sb-head span{margin-left:auto;font-size:12.5px;color:var(--sb-muted)}
  .sb-msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
  .sb-m{max-width:88%;padding:10px 13px;border-radius:14px;font-size:14.5px;line-height:1.4;white-space:pre-wrap}
  .sb-me{align-self:flex-end;background:#DCE3DF;border-bottom-right-radius:4px}
  .sb-bot{align-self:flex-start;background:var(--sb-canvas);color:#fff;border-bottom-left-radius:4px}
  .sb-src{display:block;margin-top:7px;padding-top:6px;border-top:1px solid rgba(255,255,255,.2);font-size:12px;color:var(--sb-mint)}
  .sb-hand{align-self:stretch;background:#fff;border:1px dashed #B9C4BF;border-radius:10px;padding:9px 12px;font-size:13px;color:#3A4A52}
  .sb-hand b{color:var(--sb-ink)}
  .sb-typing{align-self:flex-start;background:var(--sb-canvas);border-radius:14px;padding:12px 14px;display:flex;gap:5px}
  .sb-typing i{width:7px;height:7px;border-radius:50%;background:#fff;opacity:.5;animation:sb-b .9s infinite}
  .sb-typing i:nth-child(2){animation-delay:.15s}.sb-typing i:nth-child(3){animation-delay:.3s}
  @keyframes sb-b{0%,100%{transform:translateY(0);opacity:.4}50%{transform:translateY(-5px);opacity:1}}
  .sb-form{display:flex;gap:8px;padding:12px;border-top:1px solid #D7DEDA;background:#fff}
  .sb-form input{flex:1;border:1px solid #C9D2CD;border-radius:10px;padding:10px 12px;font:inherit;font-size:14.5px;outline:none}
  .sb-form input:focus{border-color:var(--sb-canvas)}
  .sb-form button{border:0;border-radius:10px;background:var(--sb-canvas);color:#fff;padding:0 14px;font-weight:700;cursor:pointer}
  .sb-form button:disabled{opacity:.5;cursor:default}
  .sb-foot{display:flex;justify-content:space-between;padding:6px 14px 10px;background:#fff;font-size:12px;color:var(--sb-muted)}
  .sb-foot button{border:0;background:none;color:var(--sb-ink);font-weight:700;cursor:pointer;font-size:12px;text-decoration:underline}
  @media (max-width:480px){.sb-panel{right:-8px;width:calc(100vw - 16px)}}`;

  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  const root = document.createElement("div");
  root.className = "sb-root";
  root.innerHTML = `
    <div class="sb-panel" role="dialog" aria-label="${title}">
      <div class="sb-head"><div class="sb-dot"></div><b>${title}</b><span>answers from our documents</span></div>
      <div class="sb-msgs"></div>
      <form class="sb-form"><input type="text" placeholder="Type your question" autocomplete="off" maxlength="2000"><button type="submit">Send</button></form>
      <div class="sb-foot"><span>Sources shown with every answer</span><button type="button" class="sb-human">Talk to a person</button></div>
    </div>
    <button class="sb-fab" aria-label="Open support chat">💬</button>`;
  document.body.appendChild(root);

  const msgs = root.querySelector(".sb-msgs");
  const form = root.querySelector(".sb-form");
  const input = form.querySelector("input");
  const send = form.querySelector("button");
  const fab = root.querySelector(".sb-fab");

  function add(cls, text) {
    const el = document.createElement("div");
    el.className = "sb-m " + cls;
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }
  function addHandover(text) {
    const el = document.createElement("div");
    el.className = "sb-hand";
    el.innerHTML = "<b>Handover:</b> " + text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  }
  function typing(on) {
    let t = msgs.querySelector(".sb-typing");
    if (on && !t) { t = document.createElement("div"); t.className = "sb-typing"; t.innerHTML = "<i></i><i></i><i></i>"; msgs.appendChild(t); msgs.scrollTop = msgs.scrollHeight; }
    if (!on && t) t.remove();
  }

  fab.addEventListener("click", () => {
    root.classList.toggle("open");
    if (root.classList.contains("open")) { if (!msgs.children.length) add("sb-bot", greeting); input.focus(); }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    add("sb-me", text);
    input.value = ""; send.disabled = true; typing(true);
    try {
      const r = await fetch(endpoint + "/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }) });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      sessionId = d.session_id; sessionStorage.setItem("sb-session", sessionId);
      typing(false);
      const el = add("sb-bot", d.answer);
      if (d.sources && d.sources.length) {
        const s = document.createElement("span"); s.className = "sb-src";
        s.textContent = "From " + d.sources.map(x => x.file + ", page " + x.page).join("; ");
        el.appendChild(s);
      }
      if (d.handover) addHandover("sent to the team with the full chat. You will hear from a person.");
    } catch (err) {
      typing(false);
      add("sb-bot", "Sorry, something went wrong on our side. Please try again in a moment.");
      console.error("[support-bot]", err);
    } finally { send.disabled = false; input.focus(); }
  });

  root.querySelector(".sb-human").addEventListener("click", async () => {
    if (!sessionId) { sessionId = crypto.randomUUID().replace(/-/g, ""); sessionStorage.setItem("sb-session", sessionId); }
    try {
      await fetch(endpoint + "/api/handover", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId }) });
      addHandover("a person will take over this conversation.");
    } catch (err) { console.error("[support-bot]", err); }
  });
})();
