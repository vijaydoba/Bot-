(function () {
  const CHATBOT_ID = window.AIChatbotId;
  const API_URL = window.AIChatbotApiUrl || "http://localhost:8000";

  if (!CHATBOT_ID) {
    console.warn("AIChatbot: window.AIChatbotId not set");
    return;
  }

  let sessionId = sessionStorage.getItem("ai_chat_session") || null;
  let isOpen = false;

  const styles = `
    #ai-chat-bubble {
      position: fixed; bottom: 24px; right: 24px; width: 60px; height: 60px;
      border-radius: 50%; background: var(--ai-color, #4F46E5); cursor: pointer;
      display: flex; align-items: center; justify-content: center; z-index: 9999;
      box-shadow: 0 4px 20px rgba(79,70,229,0.45); transition: transform .2s, box-shadow .2s;
    }
    #ai-chat-bubble:hover { transform: scale(1.1); box-shadow: 0 6px 28px rgba(79,70,229,0.55); }
    #ai-chat-bubble svg { width: 28px; height: 28px; fill: white; }

    #ai-chat-box {
      position: fixed; bottom: 96px; right: 24px; width: 360px; height: 540px;
      background: #fff; border-radius: 20px;
      box-shadow: 0 12px 48px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08);
      display: none; flex-direction: column; z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      overflow: hidden; animation: ai-slide-up .25s ease;
    }
    @keyframes ai-slide-up {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    #ai-chat-header {
      background: var(--ai-color, #4F46E5); color: #fff;
      padding: 16px 18px; display: flex; align-items: center; gap: 10px;
      flex-shrink: 0;
    }
    #ai-chat-header .avatar {
      width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.2);
      display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;
    }
    #ai-chat-header .info { flex: 1; }
    #ai-chat-header .info .name { font-weight: 700; font-size: 15px; }
    #ai-chat-header .info .status { font-size: 12px; opacity: .8; display: flex; align-items: center; gap: 5px; margin-top: 2px; }
    #ai-chat-header .info .status .dot { width: 7px; height: 7px; background: #4ade80; border-radius: 50%; }
    #ai-chat-close {
      background: none; border: none; color: white; cursor: pointer;
      font-size: 22px; line-height: 1; opacity: .8; padding: 0 2px;
    }
    #ai-chat-close:hover { opacity: 1; }

    #ai-chat-messages {
      flex: 1; overflow-y: auto; padding: 16px 14px 8px;
      display: flex; flex-direction: column; gap: 10px; background: #f8f9fb;
      scroll-behavior: smooth;
    }
    #ai-chat-messages::-webkit-scrollbar { width: 4px; }
    #ai-chat-messages::-webkit-scrollbar-track { background: transparent; }
    #ai-chat-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }

    .ai-msg-row { display: flex; align-items: flex-end; gap: 7px; }
    .ai-msg-row.user { flex-direction: row-reverse; }
    .ai-msg-row .bot-icon {
      width: 28px; height: 28px; border-radius: 50%;
      background: var(--ai-color, #4F46E5); display: flex; align-items: center;
      justify-content: center; font-size: 14px; flex-shrink: 0; margin-bottom: 2px;
    }

    .ai-msg {
      max-width: 78%; padding: 11px 14px; border-radius: 16px;
      font-size: 14px; line-height: 1.55; word-break: break-word;
    }
    .ai-msg.bot {
      background: #fff; border: 1px solid #e8eaed;
      border-bottom-left-radius: 4px; color: #1f2937;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .ai-msg.user {
      background: var(--ai-color, #4F46E5); color: #fff;
      border-bottom-right-radius: 4px;
    }
    .ai-msg strong { font-weight: 600; }
    .ai-msg ul { margin: 6px 0 2px 0; padding-left: 18px; }
    .ai-msg ul li { margin-bottom: 3px; }

    .ai-chips {
      display: flex; flex-wrap: wrap; gap: 7px;
      padding: 4px 0 4px 35px;
    }
    .ai-chip {
      background: #fff; border: 1.5px solid var(--ai-color, #4F46E5);
      color: var(--ai-color, #4F46E5); border-radius: 999px;
      padding: 6px 14px; font-size: 13px; cursor: pointer;
      transition: background .15s, color .15s; white-space: nowrap;
      font-family: inherit;
    }
    .ai-chip:hover { background: var(--ai-color, #4F46E5); color: #fff; }

    .ai-capture-card {
      background: #fff; border: 1.5px solid #e8eaed; border-radius: 16px;
      border-bottom-left-radius: 4px; padding: 14px 16px; margin-left: 35px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06); max-width: 90%;
    }
    .ai-capture-card p {
      margin: 0 0 12px; font-size: 13px; color: #374151; font-weight: 600;
    }
    .ai-capture-card input {
      width: 100%; box-sizing: border-box; border: 1.5px solid #e5e7eb;
      border-radius: 8px; padding: 8px 12px; font-size: 13px; margin-bottom: 8px;
      outline: none; font-family: inherit; transition: border-color .2s;
    }
    .ai-capture-card input:focus { border-color: var(--ai-color, #4F46E5); }
    .ai-capture-card button {
      width: 100%; background: var(--ai-color, #4F46E5); color: #fff;
      border: none; border-radius: 8px; padding: 10px; font-size: 14px;
      font-weight: 600; cursor: pointer; font-family: inherit; transition: opacity .2s;
    }
    .ai-capture-card button:hover { opacity: .88; }
    .ai-capture-success {
      background: #ecfdf5; border: 1.5px solid #6ee7b7; border-radius: 16px;
      border-bottom-left-radius: 4px; padding: 14px 16px; margin-left: 35px;
      font-size: 14px; color: #065f46; max-width: 90%;
    }

    .ai-time { font-size: 11px; color: #9ca3af; text-align: center; margin: 4px 0; }

    .ai-typing-row { display: flex; align-items: center; gap: 7px; }
    .ai-typing-row .bot-icon {
      width: 28px; height: 28px; border-radius: 50%;
      background: var(--ai-color, #4F46E5); display: flex; align-items: center;
      justify-content: center; font-size: 14px; flex-shrink: 0;
    }
    .ai-typing-dots {
      background: #fff; border: 1px solid #e8eaed; border-radius: 16px;
      border-bottom-left-radius: 4px; padding: 12px 16px;
      display: flex; gap: 5px; align-items: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .ai-typing-dots span {
      width: 7px; height: 7px; border-radius: 50%;
      background: #9ca3af; display: inline-block;
      animation: ai-bounce 1.2s infinite ease-in-out;
    }
    .ai-typing-dots span:nth-child(2) { animation-delay: .2s; }
    .ai-typing-dots span:nth-child(3) { animation-delay: .4s; }
    @keyframes ai-bounce {
      0%, 80%, 100% { transform: scale(0.7); opacity: .5; }
      40% { transform: scale(1); opacity: 1; }
    }

    #ai-chat-input-row {
      display: flex; padding: 12px 14px; border-top: 1px solid #f0f0f0;
      gap: 8px; background: #fff; flex-shrink: 0;
    }
    #ai-chat-input {
      flex: 1; border: 1.5px solid #e5e7eb; border-radius: 24px;
      padding: 10px 16px; font-size: 14px; outline: none;
      transition: border-color .2s; font-family: inherit; background: #f9fafb;
    }
    #ai-chat-input:focus { border-color: var(--ai-color, #4F46E5); background: #fff; }
    #ai-chat-send {
      background: var(--ai-color, #4F46E5); color: #fff; border: none;
      border-radius: 50%; width: 40px; height: 40px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: opacity .2s; flex-shrink: 0;
    }
    #ai-chat-send:hover { opacity: .85; }
    #ai-chat-send svg { width: 18px; height: 18px; fill: white; }
  `;

  const styleEl = document.createElement("style");
  styleEl.textContent = styles;
  document.head.appendChild(styleEl);

  // Bubble
  const bubble = document.createElement("div");
  bubble.id = "ai-chat-bubble";
  bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>`;

  // Chat box
  const box = document.createElement("div");
  box.id = "ai-chat-box";
  box.innerHTML = `
    <div id="ai-chat-header">
      <div class="avatar">🤖</div>
      <div class="info">
        <div class="name" id="ai-chat-title">AI Assistant</div>
        <div class="status"><span class="dot"></span>Online · Replies instantly</div>
      </div>
      <button id="ai-chat-close" title="Close">✕</button>
    </div>
    <div id="ai-chat-messages"></div>
    <div id="ai-chat-input-row">
      <input id="ai-chat-input" placeholder="Type a message…" autocomplete="off" />
      <button id="ai-chat-send">
        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(box);

  // Load bot info
  fetch(`${API_URL}/chatbots/${CHATBOT_ID}`)
    .then(r => r.json())
    .then(bot => {
      document.getElementById("ai-chat-title").textContent = bot.business_name || "AI Assistant";
      if (bot.widget_color) {
        document.documentElement.style.setProperty("--ai-color", bot.widget_color);
      }
      addBotMessage(bot.welcome_message || "Hi! How can I help you today?");
    })
    .catch(() => addBotMessage("Hi! How can I help you today?"));

  // Toggle open/close
  bubble.addEventListener("click", () => toggleChat(true));
  document.getElementById("ai-chat-close").addEventListener("click", () => toggleChat(false));

  function toggleChat(open) {
    isOpen = open;
    box.style.display = isOpen ? "flex" : "none";
    if (isOpen) document.getElementById("ai-chat-input").focus();
  }

  document.getElementById("ai-chat-send").addEventListener("click", sendMessage);
  document.getElementById("ai-chat-input").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  // ── Markdown renderer (bold + lists) ──────────────────────────────────────
  function renderMarkdown(text) {
    // Remove lines that are just dashes followed by bold option labels for chip extraction
    let html = text
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      // Bold **text** or __text__
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/__(.+?)__/g, "<strong>$1</strong>")
      // Convert "- item" or "* item" list lines into <ul><li>
      .replace(/(?:^|\n)[*\-] (.+)/g, "\n<li>$1</li>")
      .replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>")
      // Collapse consecutive </ul><ul>
      .replace(/<\/ul>\s*<ul>/g, "")
      // Line breaks
      .replace(/\n/g, "<br>");
    return html;
  }

  // ── Extract quick-reply chips from bot message ─────────────────────────────
  function extractChips(text) {
    const chips = [];
    // Match lines like "- Book an appointment" or "* Pricing" or numbered "1. Services"
    const listPattern = /(?:^|\n)[\-\*\d\.]+\s+\*{0,2}([^*\n]+?)\*{0,2}(?:\n|$)/g;
    let match;
    while ((match = listPattern.exec(text)) !== null) {
      const label = match[1].trim();
      if (label.length > 2 && label.length < 50 && chips.length < 5) {
        chips.push(label);
      }
    }
    return chips;
  }

  // ── Add bot message ────────────────────────────────────────────────────────
  function addBotMessage(text) {
    const msgs = document.getElementById("ai-chat-messages");

    const row = document.createElement("div");
    row.className = "ai-msg-row";

    const icon = document.createElement("div");
    icon.className = "bot-icon";
    icon.textContent = "🤖";

    const bubble = document.createElement("div");
    bubble.className = "ai-msg bot";
    bubble.innerHTML = renderMarkdown(text);

    row.appendChild(icon);
    row.appendChild(bubble);
    msgs.appendChild(row);

    // Handoff detection — show lead capture form
    if (isHandoff(text) && !document.getElementById("ai-capture-form")) {
      setTimeout(() => showCaptureForm(msgs), 600);
    }

    // Quick-reply chips
    const chips = extractChips(text);
    if (chips.length > 0) {
      const chipRow = document.createElement("div");
      chipRow.className = "ai-chips";
      chips.forEach(label => {
        const btn = document.createElement("button");
        btn.className = "ai-chip";
        btn.textContent = label;
        btn.addEventListener("click", () => {
          chipRow.remove();
          sendText(label);
        });
        chipRow.appendChild(btn);
      });
      msgs.appendChild(chipRow);
    }

    scrollBottom();
  }

  function addUserMessage(text) {
    const msgs = document.getElementById("ai-chat-messages");
    const row = document.createElement("div");
    row.className = "ai-msg-row user";
    const bubble = document.createElement("div");
    bubble.className = "ai-msg user";
    bubble.textContent = text;
    row.appendChild(bubble);
    msgs.appendChild(row);
    scrollBottom();
  }

  function showTyping() {
    const msgs = document.getElementById("ai-chat-messages");
    const row = document.createElement("div");
    row.className = "ai-typing-row";
    row.id = "ai-typing";
    row.innerHTML = `
      <div class="bot-icon">🤖</div>
      <div class="ai-typing-dots"><span></span><span></span><span></span></div>
    `;
    msgs.appendChild(row);
    scrollBottom();
  }

  function hideTyping() {
    const el = document.getElementById("ai-typing");
    if (el) el.remove();
  }

  function scrollBottom() {
    const msgs = document.getElementById("ai-chat-messages");
    msgs.scrollTop = msgs.scrollHeight;
  }

  // ── Handoff detection ─────────────────────────────────────────────────────
  function isHandoff(text) {
    const t = text.toLowerCase();
    return [
      "connect you with", "team member", "someone will", "get back to you",
      "human agent", "our staff", "reach out to you", "contact you",
      "follow up", "we will call", "we'll call", "someone from our"
    ].some(phrase => t.includes(phrase));
  }

  // ── Lead capture form ─────────────────────────────────────────────────────
  function showCaptureForm(container) {
    const card = document.createElement("div");
    card.className = "ai-capture-card";
    card.id = "ai-capture-form";
    card.innerHTML = `
      <p>Leave your details and we'll contact you shortly:</p>
      <input id="ai-cap-name"  type="text"  placeholder="Your name"  />
      <input id="ai-cap-email" type="email" placeholder="Email address" />
      <input id="ai-cap-phone" type="tel"   placeholder="Phone number (optional)" />
      <button id="ai-cap-submit">Send my details</button>
    `;
    container.appendChild(card);
    scrollBottom();

    document.getElementById("ai-cap-submit").addEventListener("click", () => {
      const name  = document.getElementById("ai-cap-name").value.trim();
      const email = document.getElementById("ai-cap-email").value.trim();
      const phone = document.getElementById("ai-cap-phone").value.trim();
      if (!name || !email) {
        document.getElementById("ai-cap-name").style.borderColor  = name  ? "" : "#ef4444";
        document.getElementById("ai-cap-email").style.borderColor = email ? "" : "#ef4444";
        return;
      }
      const btn = document.getElementById("ai-cap-submit");
      btn.textContent = "Sending…";
      btn.disabled = true;

      fetch(`${API_URL}/leads/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chatbot_id: CHATBOT_ID, session_id: sessionId, name, email, phone }),
      })
        .then(r => r.json())
        .then(() => {
          card.outerHTML = `<div class="ai-capture-success">✅ Got it, <strong>${name}</strong>! A team member will contact you at <strong>${email}</strong> soon.</div>`;
          scrollBottom();
        })
        .catch(() => {
          btn.textContent = "Try again";
          btn.disabled = false;
        });
    });
  }

  function sendMessage() {
    const input = document.getElementById("ai-chat-input");
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendText(text);
  }

  function sendText(text) {
    // Remove any existing chips so conversation stays clean
    document.querySelectorAll(".ai-chips").forEach(el => el.remove());

    addUserMessage(text);
    showTyping();

    fetch(`${API_URL}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chatbot_id: CHATBOT_ID, message: text, session_id: sessionId }),
    })
      .then(r => r.json())
      .then(data => {
        hideTyping();
        sessionId = data.session_id;
        sessionStorage.setItem("ai_chat_session", sessionId);
        addBotMessage(data.reply);
      })
      .catch(() => {
        hideTyping();
        addBotMessage("Sorry, something went wrong. Please try again.");
      });
  }
})();
