(function () {
  const API_URL = "/api/chat";

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function getQueryParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  }

  function dismissWelcome(messagesEl) {
    const welcome = document.getElementById("chat-welcome");
    if (welcome) welcome.remove();
    messagesEl.classList.add("chat-messages--conversation");
  }

  function renderUserMessage(text) {
    const wrap = document.createElement("div");
    wrap.className = "message message--user";
    wrap.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    return wrap;
  }

  function renderAssistantMessage(data) {
    const isRefusal = Boolean(data.is_refusal);
    const wrap = document.createElement("div");
    wrap.className = `message message--assistant${isRefusal ? " message--refusal" : ""}`;
    wrap.innerHTML = `
      <div class="message-bubble">
        ${escapeHtml(data.answer || data.message || "")}
        ${
          data.citation_url
            ? `<div class="message-citation">
                <a href="${escapeHtml(data.citation_url)}" target="_blank" rel="noopener noreferrer">
                  ${isRefusal ? "Learn more →" : "View source →"}
                </a>
              </div>`
            : ""
        }
        ${
          data.last_updated
            ? `<div class="message-footer-date">Last updated from sources: ${escapeHtml(data.last_updated)}</div>`
            : ""
        }
      </div>
      ${
        data.disclaimer
          ? `<div class="message-meta">${escapeHtml(data.disclaimer)}</div>`
          : ""
      }`;
    return wrap;
  }

  function renderErrorMessage(text) {
    const wrap = document.createElement("div");
    wrap.className = "message message--assistant message--refusal";
    wrap.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    return wrap;
  }

  function renderLoadingIndicator() {
    const loading = document.createElement("div");
    loading.className = "chat-loading";
    loading.id = "chat-loading";
    loading.textContent = "Retrieving verified facts…";
    return loading;
  }

  function scrollToBottom(messagesEl) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function buildWelcome() {
    const welcome = document.createElement("div");
    welcome.className = "chat-welcome";
    welcome.id = "chat-welcome";

    const title = document.createElement("h1");
    title.textContent = "Facts Only Assistant";

    const subtitle = document.createElement("p");
    subtitle.textContent =
      "Ask factual questions about 12 HDFC schemes — expense ratio, exit load, fund managers, benchmarks, and more.";

    const chips = document.createElement("div");
    chips.className = "chip-row";

    (window.EXAMPLE_QUESTIONS || []).forEach((question) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip example-chip";
      chip.textContent = question;
      chips.appendChild(chip);
    });

    const privacy = document.createElement("p");
    privacy.className = "privacy-note";
    privacy.textContent = "Do not share PAN, Aadhaar, phone, or account details.";

    welcome.append(title, subtitle, chips, privacy);
    return welcome;
  }

  async function sendMessage(text, messagesEl, inputEl, sendBtn, errorEl) {
    const trimmed = text.trim();
    if (!trimmed) return;

    dismissWelcome(messagesEl);
    errorEl.classList.add("hidden");
    errorEl.textContent = "";
    inputEl.disabled = true;
    sendBtn.disabled = true;

    messagesEl.appendChild(renderUserMessage(trimmed));
    scrollToBottom(messagesEl);

    const loading = renderLoadingIndicator();
    messagesEl.appendChild(loading);
    scrollToBottom(messagesEl);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      });

      loading.remove();

      if (!response.ok) {
        let detail = "Could not fetch an answer. Please try again.";
        try {
          const err = await response.json();
          if (typeof err.detail === "string") detail = err.detail;
          else if (Array.isArray(err.detail)) detail = err.detail.map((d) => d.msg).join(", ");
        } catch (_) {
          /* ignore parse errors */
        }
        throw new Error(detail);
      }

      const data = await response.json();
      messagesEl.appendChild(renderAssistantMessage(data));
    } catch (err) {
      loading.remove();
      const message = err.message || "Something went wrong. Please try again.";
      messagesEl.appendChild(renderErrorMessage(message));
      errorEl.textContent = message;
      errorEl.classList.remove("hidden");
    } finally {
      inputEl.disabled = false;
      sendBtn.disabled = false;
      inputEl.focus();
      scrollToBottom(messagesEl);
    }
  }

  window.initChat = function initChat() {
    const messagesEl = document.getElementById("chat-messages");
    const inputEl = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send");
    const formEl = document.getElementById("chat-form");
    const errorEl = document.getElementById("chat-error");

    if (!messagesEl || !inputEl || !sendBtn || !formEl || !errorEl) {
      console.error("Chat UI elements missing — check assistant.html markup.");
      return;
    }

    messagesEl.innerHTML = "";
    messagesEl.appendChild(buildWelcome());

    messagesEl.addEventListener("click", (event) => {
      const chip = event.target.closest(".example-chip");
      if (!chip) return;
      sendMessage(chip.textContent || "", messagesEl, inputEl, sendBtn, errorEl);
    });

    formEl.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = inputEl.value;
      inputEl.value = "";
      sendMessage(text, messagesEl, inputEl, sendBtn, errorEl);
    });

    const prefill = getQueryParam("q");
    if (prefill) {
      sendMessage(prefill, messagesEl, inputEl, sendBtn, errorEl);
    }
  };

  window.prefillChatInput = function prefillChatInput(scheme) {
    const inputEl = document.getElementById("chat-input");
    if (!inputEl || !scheme) return;
    inputEl.placeholder = `Ask a factual question about ${scheme.shortName}…`;
  };
})();
