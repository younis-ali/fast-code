(function () {
  "use strict";

  var conversations = [];
  var activeConversationId = null;
  var abortController = null;
  var isStreaming = false;
  var acSelectedIdx = -1;
  var acEntries = [];
  var acVisible = false;

  var messagesEl   = document.getElementById("messages");
  var chatForm     = document.getElementById("chat-form");
  var chatInput    = document.getElementById("chat-input");
  var sendBtn      = document.getElementById("send-btn");
  var newChatBtn   = document.getElementById("new-chat-btn");
  var convList     = document.getElementById("conversation-list");
  var modelSelect  = document.getElementById("model-select");
  var modeSelect   = document.getElementById("chat-mode-select");
  var statusDot    = document.getElementById("status-indicator");
  var emptyState   = document.getElementById("empty-state");
  var scrollAnchor = document.getElementById("chat-scroll-anchor");
  var autoApprove  = document.getElementById("auto-approve-toggle");
  var acDropdown   = document.getElementById("file-autocomplete");
  var activityLabelEl = document.getElementById("activity-label");
  var mainEl = document.querySelector("main");
  var themeToggle = document.getElementById("theme-toggle");
  var deleteModal = document.getElementById("delete-modal");
  var deleteModalCancel = document.getElementById("delete-modal-cancel");
  var deleteModalConfirm = document.getElementById("delete-modal-confirm");
  var deleteModalHeading = document.getElementById("delete-modal-heading");
  var pendingDeleteConvId = null;

  function toggleTheme() {
    var isLight = document.documentElement.getAttribute("data-theme") === "light";
    try {
      if (isLight) {
        document.documentElement.removeAttribute("data-theme");
        localStorage.setItem("fast-code-theme", "dark");
      } else {
        document.documentElement.setAttribute("data-theme", "light");
        localStorage.setItem("fast-code-theme", "light");
      }
    } catch (e) {
      if (isLight) document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", "light");
    }
  }

  function openDeleteModal(convId) {
    pendingDeleteConvId = convId;
    var conv = conversations.find(function (c) { return c.id === convId; });
    var label = (conv && conv.title) ? conv.title : "this chat";
    if (deleteModalHeading) {
      deleteModalHeading.textContent = "Delete “" + label.slice(0, 48) + (label.length > 48 ? "…" : "") + "”?";
    }
    if (deleteModal) {
      deleteModal.classList.remove("hidden");
      deleteModal.setAttribute("aria-hidden", "false");
    }
  }

  function closeDeleteModal() {
    pendingDeleteConvId = null;
    if (deleteModal) {
      deleteModal.classList.add("hidden");
      deleteModal.setAttribute("aria-hidden", "true");
    }
  }

  async function confirmDeleteConversation() {
    var convId = pendingDeleteConvId;
    closeDeleteModal();
    if (!convId) return;

    var idx = conversations.findIndex(function (c) { return c.id === convId; });
    if (idx < 0) return;
    var conv = conversations[idx];

    if (isStreaming && activeConversationId === convId && abortController) {
      try { abortController.abort(); } catch (e) {}
    }

    if (conv.hasServerId && conv.id && String(conv.id).indexOf("pending_") !== 0) {
      try {
        var resp = await fetch("/api/conversations/" + encodeURIComponent(conv.id), { method: "DELETE" });
        if (!resp.ok) {
          alert("Could not delete this conversation. Try again.");
          return;
        }
      } catch (e) {
        alert("Could not delete this conversation. Check your connection.");
        return;
      }
    }

    conversations.splice(idx, 1);

    if (activeConversationId === convId) {
      if (conversations.length === 0) {
        await newConversation();
      } else {
        activeConversationId = conversations[0].id;
        switchConversation(activeConversationId);
      }
    } else {
      renderConversations();
    }
  }

  function setStatus(state) {
    statusDot.className = state;
    statusDot.title = state === "loading" ? "Busy" : state === "error" ? "Error" : "Ready";
  }

  function setActivityText(text) {
    if (!activityLabelEl) return;
    activityLabelEl.textContent = text || "";
    activityLabelEl.style.display = text ? "inline" : "none";
  }

  function clearActivity() {
    setActivityText("");
  }

  var MODE_PLACEHOLDERS = {
    agent: "Message Fast Code... (type / for files)",
    ask: "Ask a question — read-only mode, no edits or commands",
    plan: "Describe what to plan — exploration only, then a written plan",
  };

  function applyChatModePlaceholder() {
    if (!chatInput || !modeSelect) return;
    var m = modeSelect.value || "agent";
    chatInput.placeholder = MODE_PLACEHOLDERS[m] || MODE_PLACEHOLDERS.agent;
  }

  function toolActionTitle(name) {
    var titles = {
      Bash: "Run command",
      Read: "Read file",
      Write: "Write file",
      Edit: "Apply edit",
      Glob: "Find files",
      Grep: "Search in files",
      WebFetch: "Fetch URL",
      WebSearch: "Web search",
      NotebookEdit: "Edit notebook",
      TodoWrite: "Tasks",
      Agent: "Delegated task",
      Coder: "Code changes",
    };
    return titles[name] || "Tool";
  }

  function toolActivityLine(name) {
    var lines = {
      Bash: "Running command",
      Read: "Reading file",
      Write: "Writing file",
      Edit: "Editing file",
      Glob: "Searching files",
      Grep: "Searching text",
      WebFetch: "Loading page",
      WebSearch: "Searching the web",
      NotebookEdit: "Updating notebook",
      TodoWrite: "Updating tasks",
      Agent: "Running sub-task",
      Coder: "Applying code changes",
    };
    return lines[name] || "Working";
  }

  function badgeLabel(status) {
    if (status === "done") return "Finished";
    if (status === "error") return "Failed";
    if (status === "running") return "Working";
    if (status === "pending") return "Needs approval";
    if (status === "denied") return "Skipped";
    return "Queued";
  }

  function scrollToBottom() {
    function run() {
      if (scrollAnchor && scrollAnchor.parentNode === messagesEl) {
        scrollAnchor.scrollIntoView({ block: "end", behavior: "auto" });
      }
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    requestAnimationFrame(function () {
      requestAnimationFrame(run);
    });
  }

  function escapeHtml(str) {
    var d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function formatContent(text) {
    var html = escapeHtml(text);
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function (_, lang, code) {
      return "<pre><code>" + code.trim() + "</code></pre>";
    });
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    return html;
  }

  function toolIconClass(name) {
    if (name === "Bash") return "cmd";
    if (name === "Read" || name === "Write" || name === "Edit" || name === "NotebookEdit") return "file";
    if (name === "Glob" || name === "Grep") return "search";
    if (name === "WebFetch" || name === "WebSearch") return "web";
    if (name === "Agent" || name === "Coder") return "search";
    return "cmd";
  }

  function toolIconChar(name) {
    if (name === "Bash") return ">";
    if (name === "Read") return "R";
    if (name === "Write" || name === "Edit") return "W";
    if (name === "Glob" || name === "Grep") return "S";
    if (name === "WebFetch" || name === "WebSearch") return "W";
    if (name === "Agent") return "A";
    if (name === "Coder") return "C";
    return "T";
  }

  function toolSummary(name, input) {
    if (!input) return "";
    if (name === "Bash") return (input.command || "").slice(0, 80);
    if (name === "Read") return input.file_path || "";
    if (name === "Write") return input.file_path || "";
    if (name === "Edit") return input.file_path || "";
    if (name === "Glob") return input.pattern || "";
    if (name === "Grep") return input.pattern || "";
    if (name === "WebFetch") return input.url || "";
    if (name === "WebSearch") return input.query || "";
    if (name === "Agent" || name === "Coder") return (input.description || input.prompt || "").slice(0, 80);
    return JSON.stringify(input).slice(0, 60);
  }

  function getActive() {
    return conversations.find(function (c) { return c.id === activeConversationId; });
  }

  function renderConversations() {
    convList.innerHTML = "";
    conversations.forEach(function (c) {
      var li = document.createElement("li");
      li.className = "conv-item";
      li.dataset.id = c.id;
      if (c.id === activeConversationId) li.classList.add("active");

      var titleSpan = document.createElement("span");
      titleSpan.className = "conv-item-title";
      titleSpan.textContent = c.title || "New Chat";
      titleSpan.title = c.title || "New Chat";

      var delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "conv-delete-btn";
      delBtn.title = "Delete conversation";
      delBtn.setAttribute("aria-label", "Delete conversation");
      delBtn.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">' +
        '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>' +
        "</svg>";

      li.appendChild(titleSpan);
      li.appendChild(delBtn);

      li.addEventListener("click", function (e) {
        if (e.target.closest(".conv-delete-btn")) return;
        switchConversation(c.id);
      });
      delBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        openDeleteModal(c.id);
      });

      convList.appendChild(li);
    });
  }

  async function newConversation() {
    var conv = { id: null, title: "New Chat", hasServerId: false, uiMessages: [] };
    try {
      var resp = await fetch("/api/conversations?title=" + encodeURIComponent("New Conversation"), { method: "POST" });
      if (resp.ok) { var data = await resp.json(); conv.id = data.id; conv.hasServerId = true; conv.title = data.title || "New Chat"; }
    } catch (e) { console.warn("pre-create failed", e); }
    if (!conv.id) { conv.id = "pending_" + Math.random().toString(36).slice(2, 14); }
    conversations.unshift(conv);
    activeConversationId = conv.id;
    renderConversations();
    renderMessages();
  }

  function switchConversation(id) {
    activeConversationId = id;
    renderConversations();
    var conv = getActive();
    if (conv && conv.hasServerId && conv.uiMessages.length === 0) { hydrateConversation(conv); }
    else { renderMessages(); }
  }

  async function hydrateConversation(conv) {
    try {
      var resp = await fetch("/api/conversations/" + encodeURIComponent(conv.id));
      if (!resp.ok) { renderMessages(); return; }
      var data = await resp.json();
      conv.title = data.title || conv.title;
      conv.uiMessages = [];
      if (data.messages) {
        for (var i = 0; i < data.messages.length; i++) {
          var m = data.messages[i];
          if (m.role === "user") {
            var txt = contentToString(m.content);
            if (txt) conv.uiMessages.push({ role: "user", content: txt });
          } else if (m.role === "assistant") {
            var parsed = parseAssistant(m.content);
            conv.uiMessages.push({
              role: "assistant",
              text: parsed.text,
              toolCalls: parsed.toolCalls,
              blocks: parsed.blocks,
            });
          }
        }
      }
    } catch (e) { console.warn("hydrate failed", e); }
    renderMessages();
  }

  function contentToString(content) {
    if (typeof content === "string") return content;
    if (!Array.isArray(content)) return "";
    var parts = [];
    for (var i = 0; i < content.length; i++) { if (content[i] && content[i].type === "text") parts.push(content[i].text || ""); }
    return parts.join("\n").trim();
  }

  function parseAssistant(content) {
    var out = { text: "", toolCalls: [], blocks: [] };
    if (typeof content === "string") {
      out.text = content;
      out.blocks = [{ type: "text", text: content }];
      return out;
    }
    if (!Array.isArray(content)) return out;
    for (var i = 0; i < content.length; i++) {
      var b = content[i];
      if (!b || !b.type) continue;
      if (b.type === "text") {
        var t = b.text || "";
        out.text += t;
        if (t) out.blocks.push({ type: "text", text: t });
      } else if (b.type === "tool_use") {
        var tc = { name: b.name, input: b.input, id: b.id };
        out.toolCalls.push(tc);
        out.blocks.push({ type: "tool", name: b.name, input: b.input, id: b.id });
      }
    }
    return out;
  }

  function moveScrollAnchorToEnd() {
    if (scrollAnchor && scrollAnchor.parentNode) {
      scrollAnchor.parentNode.appendChild(scrollAnchor);
    }
  }

  function renderMessages() {
    var conv = getActive();
    while (messagesEl.firstChild) {
      messagesEl.removeChild(messagesEl.firstChild);
    }
    messagesEl.appendChild(emptyState);
    messagesEl.appendChild(scrollAnchor);

    if (!conv || conv.uiMessages.length === 0) {
      emptyState.style.display = "flex";
      scrollToBottom();
      return;
    }
    emptyState.style.display = "none";

    conv.uiMessages.forEach(function (msg) {
      if (msg.role === "user") appendUserRow(msg.content || "");
      else if (msg.role === "assistant") {
        var shell = createAssistantShell();
        if (msg.blocks && msg.blocks.length) {
          msg.blocks.forEach(function (blk) {
            if (blk.type === "text" && blk.text) {
              var td = document.createElement("div");
              td.className = "msg-stream-text msg-content";
              td.innerHTML = formatContent(blk.text);
              shell.stream.appendChild(td);
            } else if (blk.type === "tool") {
              appendToolCardTo(shell.stream, blk.name, blk.input, blk.result, blk.isError, "done");
            }
          });
        } else {
          if (msg.text) {
            var td2 = document.createElement("div");
            td2.className = "msg-stream-text msg-content";
            td2.innerHTML = formatContent(msg.text);
            shell.stream.appendChild(td2);
          }
          if (msg.toolCalls) {
            msg.toolCalls.forEach(function (tc) {
              appendToolCardTo(shell.stream, tc.name, tc.input, tc.result, tc.isError, "done");
            });
          }
        }
        if (msg.planBuildable && msg.planText && shell.body) {
          attachPlanBuildPanel(shell.body, conv, msg);
        }
      }
    });
    moveScrollAnchorToEnd();
    scrollToBottom();
  }

  function appendUserRow(text) {
    var row = document.createElement("div"); row.className = "msg-row";
    row.innerHTML =
      '<div class="msg-avatar user-avatar">U</div>' +
      '<div class="msg-body">' +
        '<div class="msg-role user-role">You</div>' +
        '<div class="msg-content">' + escapeHtml(text) + '</div>' +
      '</div>';
    messagesEl.insertBefore(row, scrollAnchor);
  }

  function createAssistantShell() {
    var row = document.createElement("div");
    row.className = "msg-row";
    var stream = document.createElement("div");
    stream.className = "assistant-stream";
    var bodyDiv = document.createElement("div");
    bodyDiv.className = "msg-body";
    bodyDiv.innerHTML = '<div class="msg-role ai-role">Fast Code</div>';
    bodyDiv.appendChild(stream);
    row.innerHTML =
      '<div class="msg-avatar ai-avatar" aria-hidden="true">' +
      '<img class="ai-avatar-img" src="/static/favicon.svg?v=1" width="24" height="24" alt="" decoding="async" />' +
      "</div>";
    row.appendChild(bodyDiv);
    messagesEl.insertBefore(row, scrollAnchor);
    return { row: row, stream: stream, body: bodyDiv };
  }

  function buildPlanExecutionPrompt(planText) {
    return (
      "Implement the following plan. Work through the todos in order; use TodoWrite to update task status as you go. " +
      "Run tests or commands as needed to verify the implementation.\n\n--- Plan ---\n\n" +
      planText
    );
  }

  function attachPlanBuildPanel(bodyEl, conv, msg) {
    if (!bodyEl || !msg || !msg.planBuildable || !msg.planText) return;
    var existing = bodyEl.querySelector(".plan-build-panel");
    if (existing) existing.remove();

    var panel = document.createElement("div");
    panel.className = "plan-build-panel";
    panel.setAttribute("role", "region");
    panel.setAttribute("aria-label", "Plan review");

    var label = document.createElement("label");
    label.className = "plan-build-label";
    label.htmlFor = "plan-edit-" + conv.id + "-" + Math.random().toString(36).slice(2, 9);
    label.textContent = "Review or edit the plan, then build in Agent mode";

    var ta = document.createElement("textarea");
    ta.className = "plan-build-textarea";
    ta.id = label.htmlFor;
    ta.value = msg.planText;
    ta.rows = 8;
    ta.addEventListener("input", function () {
      msg.planText = ta.value;
    });

    var actions = document.createElement("div");
    actions.className = "plan-build-actions";

    var buildBtn = document.createElement("button");
    buildBtn.type = "button";
    buildBtn.className = "btn-primary btn-build-plan";
    buildBtn.textContent = "Build plan";

    buildBtn.addEventListener("click", function () {
      var text = (ta.value || "").trim();
      if (!text) return;
      msg.planBuildable = false;
      if (panel.parentNode) panel.parentNode.removeChild(panel);
      if (modeSelect) modeSelect.value = "agent";
      applyChatModePlaceholder();
      sendMessage(buildPlanExecutionPrompt(text));
    });

    actions.appendChild(buildBtn);
    panel.appendChild(label);
    panel.appendChild(ta);
    panel.appendChild(actions);
    bodyEl.appendChild(panel);
  }

  function appendToolCardTo(parent, name, input, result, isError, status) {
    var card = document.createElement("div");
    card.className = "tool-card tool-card--" + toolIconClass(name);
    card.dataset.status = status || "pending";
    card.dataset.tool = name;

    var st = status || "pending";
    var badgeClass = "tool-card-badge " + st;
    var summary = toolSummary(name, input);
    var actionTitle = toolActionTitle(name);

    card.innerHTML =
      '<div class="tool-card-header">' +
        '<span class="tool-card-chevron" aria-hidden="true">&#9654;</span>' +
        '<span class="tool-card-icon ' + toolIconClass(name) + '">' + toolIconChar(name) + '</span>' +
        '<div class="tool-card-meta">' +
          '<span class="tool-card-action">' + escapeHtml(actionTitle) + '</span>' +
          '<span class="tool-card-tech">' + escapeHtml(name) + '</span>' +
        '</div>' +
        '<span class="tool-card-summary" title="' + escapeHtml(summary) + '">' + escapeHtml(summary) + '</span>' +
        '<span class="' + badgeClass + '">' + badgeLabel(st) + '</span>' +
      '</div>' +
      '<div class="tool-card-detail">' +
        (input ? '<div class="tool-card-input">' + escapeHtml(JSON.stringify(input, null, 2)) + '</div>' : '') +
        (result !== undefined ? '<div class="tool-card-output' + (isError ? ' tool-error-output' : '') + '">' + escapeHtml(typeof result === "string" ? result : JSON.stringify(result)).slice(0, 4000) + '</div>' : '') +
      '</div>';

    card.querySelector(".tool-card-header").addEventListener("click", function () {
      card.classList.toggle("expanded");
    });

    if (st === "running" || st === "pending") {
      card.classList.add("tool-card--busy");
    }

    parent.appendChild(card);
    return card;
  }

  function updateCardStatus(card, status, result, isError) {
    card.dataset.status = status;
    if (status === "running" || status === "pending") {
      card.classList.add("tool-card--busy");
    } else {
      card.classList.remove("tool-card--busy");
    }
    var badge = card.querySelector(".tool-card-badge");
    if (badge) {
      badge.className = "tool-card-badge " + status;
      badge.textContent = badgeLabel(status);
    }
    if (result !== undefined) {
      var detail = card.querySelector(".tool-card-detail");
      var existingOutput = detail.querySelector(".tool-card-output");
      if (existingOutput) existingOutput.remove();
      var outDiv = document.createElement("div");
      outDiv.className = "tool-card-output" + (isError ? " tool-error-output" : "");
      outDiv.textContent = (typeof result === "string" ? result : JSON.stringify(result)).slice(0, 4000);
      detail.appendChild(outDiv);
    }
  }

  async function sendMessage(text) {
    var conv = getActive();
    if (!conv) return;

    conv.uiMessages.push({ role: "user", content: text });
    renderMessages();
    emptyState.style.display = "none";
    isStreaming = true;
    setStatus("loading");
    sendBtn.textContent = "Stop";
    abortController = new AbortController();

    var requestMode = modeSelect ? modeSelect.value : "agent";

    var payload = {
      messages: [{ role: "user", content: text }],
      model: modelSelect.value,
      stream: true,
      auto_approve: autoApprove.checked,
      mode: modeSelect ? modeSelect.value : "agent",
    };
    if (conv.hasServerId && conv.id && !String(conv.id).startsWith("pending_")) {
      payload.conversation_id = conv.id;
    }

    var shell = createAssistantShell();
    var stream = shell.stream;
    var assistantText = "";
    var segmentBuf = "";
    var currentTextEl = null;
    var orderedBlocks = [];
    var toolCalls = [];
    var toolCards = {};
    var thinkingEl = null;
    var sawFirstToken = false;

    if (mainEl) mainEl.classList.add("is-streaming");
    setActivityText("Preparing response");

    thinkingEl = document.createElement("div");
    thinkingEl.className = "stream-pending";
    thinkingEl.setAttribute("role", "status");
    thinkingEl.innerHTML =
      '<span class="stream-pending-bar"></span>' +
      '<span class="stream-pending-text">Working on your request</span>' +
      '<span class="stream-pending-dots" aria-hidden="true"><span></span><span></span><span></span></span>';
    stream.appendChild(thinkingEl);
    scrollToBottom();

    function hideThinking() {
      if (thinkingEl && thinkingEl.parentNode) {
        thinkingEl.parentNode.removeChild(thinkingEl);
      }
      thinkingEl = null;
    }

    function ensureTextEl() {
      if (!currentTextEl) {
        currentTextEl = document.createElement("div");
        currentTextEl.className = "msg-stream-text msg-content";
        stream.appendChild(currentTextEl);
      }
      return currentTextEl;
    }

    function flushTextSegment() {
      if (segmentBuf) {
        orderedBlocks.push({ type: "text", text: segmentBuf });
      }
      segmentBuf = "";
      currentTextEl = null;
    }

    function findBlockForTool(tid) {
      for (var i = 0; i < orderedBlocks.length; i++) {
        if (orderedBlocks[i].type === "tool" && orderedBlocks[i].id === tid) return orderedBlocks[i];
      }
      return null;
    }

    try {
      var response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: abortController.signal,
      });

      var reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = "";

      while (true) {
        var chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        var lines = buffer.split("\n");
        buffer = lines.pop();

        for (var li = 0; li < lines.length; li++) {
          var line = lines[li];
          if (!line.startsWith("data: ")) continue;
          var payloadLine = line.slice(6).trim();
          if (payloadLine === "[DONE]") continue;
          var event;
          try { event = JSON.parse(payloadLine); } catch (e) { continue; }

          switch (event.type) {
            case "message_start":
              setActivityText("Generating");
              if (event.conversation_id) syncConvId(conv, event.conversation_id);
              break;

            case "content_block_delta":
              if (event.delta && event.delta.text) {
                if (!sawFirstToken) {
                  sawFirstToken = true;
                  hideThinking();
                }
                assistantText += event.delta.text;
                segmentBuf += event.delta.text;
                var tel = ensureTextEl();
                tel.classList.add("msg-stream-live");
                tel.innerHTML = formatContent(segmentBuf);
                setActivityText("Writing response");
                scrollToBottom();
              }
              break;

            case "tool_use_start":
              break;

            case "tool_use_end":
              if (!sawFirstToken) {
                sawFirstToken = true;
                hideThinking();
              }
              flushTextSegment();
              var blk = { type: "tool", id: event.id, name: event.name, input: event.input };
              orderedBlocks.push(blk);
              setActivityText(toolActivityLine(event.name));
              var card = appendToolCardTo(stream, event.name, event.input, undefined, false, event.requires_approval ? "pending" : "running");
              toolCards[event.id] = card;
              toolCalls.push({ id: event.id, name: event.name, input: event.input });
              scrollToBottom();
              break;

            case "tool_approval_request":
              handleApprovalRequest(event, toolCards, stream);
              scrollToBottom();
              break;

            case "tool_execution_start":
              setActivityText("Running tools");
              Object.keys(toolCards).forEach(function (tid) {
                var c = toolCards[tid];
                if (c && (c.dataset.status === "pending" || c.dataset.status === "approved")) {
                  updateCardStatus(c, "running");
                }
              });
              scrollToBottom();
              break;

            case "tool_result":
              var tcard = toolCards[event.tool_use_id];
              if (tcard) {
                updateCardStatus(tcard, event.is_error ? "error" : "done", event.content, event.is_error);
              }
              setActivityText("Generating reply");
              var found = toolCalls.find(function (t) { return t.id === event.tool_use_id; });
              if (found) {
                found.result = event.content;
                found.isError = event.is_error;
              }
              var b = findBlockForTool(event.tool_use_id);
              if (b) {
                b.result = event.content;
                b.isError = event.is_error;
              }
              scrollToBottom();
              break;

            case "tool_denied":
              if (event.tool_ids) {
                event.tool_ids.forEach(function (tid) {
                  if (toolCards[tid]) updateCardStatus(toolCards[tid], "denied");
                });
              }
              scrollToBottom();
              break;

            case "message_stop":
              clearActivity();
              if (event.conversation_id) syncConvId(conv, event.conversation_id);
              break;

            case "error":
              hideThinking();
              assistantText += "\n[Error: " + (event.error || "Unknown") + "]";
              segmentBuf += "\n[Error: " + (event.error || "Unknown") + "]";
              ensureTextEl().innerHTML = formatContent(segmentBuf);
              setActivityText("Something went wrong");
              setStatus("error");
              scrollToBottom();
              break;
          }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        hideThinking();
        assistantText += "\n[Connection error: " + err.message + "]";
        segmentBuf += "\n[Connection error: " + err.message + "]";
        ensureTextEl().innerHTML = formatContent(segmentBuf);
        setActivityText("Connection problem");
        setStatus("error");
      }
    }

    hideThinking();
    var liveNodes = stream.querySelectorAll(".msg-stream-live");
    for (var ni = 0; ni < liveNodes.length; ni++) {
      liveNodes[ni].classList.remove("msg-stream-live");
    }
    flushTextSegment();
    moveScrollAnchorToEnd();

    var assistantMsg = {
      role: "assistant",
      text: assistantText,
      toolCalls: toolCalls,
      blocks: orderedBlocks,
    };
    if (requestMode === "plan" && assistantText.trim()) {
      assistantMsg.planBuildable = true;
      assistantMsg.planText = assistantText;
    }
    conv.uiMessages.push(assistantMsg);
    if (assistantMsg.planBuildable && shell.body) {
      attachPlanBuildPanel(shell.body, conv, assistantMsg);
    }
    if (conv.title === "New Chat" && text.length > 0) {
      conv.title = text.slice(0, 60);
      renderConversations();
    }

    isStreaming = false;
    abortController = null;
    if (mainEl) mainEl.classList.remove("is-streaming");
    clearActivity();
    setStatus("");
    sendBtn.textContent = "Send";
    scrollToBottom();
  }

  function handleApprovalRequest(event, toolCards, stream) {
    var requestId = event.request_id;
    var tools = event.tools || [];

    var wrapper = document.createElement("div");
    wrapper.className = "tool-approval-btns";

    var approveBtn = document.createElement("button");
    approveBtn.className = "btn-approve";
    approveBtn.textContent = "Allow All (" + tools.filter(function (t) { return t.requires_approval; }).length + ")";

    var denyBtn = document.createElement("button");
    denyBtn.className = "btn-deny";
    denyBtn.textContent = "Deny";

    var resolved = false;

    approveBtn.addEventListener("click", function () {
      if (resolved) return;
      resolved = true;
      wrapper.remove();
      tools.forEach(function (t) {
        if (toolCards[t.id]) updateCardStatus(toolCards[t.id], "running");
      });
      fetch("/api/tool-approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId, approve_all: true }),
      });
    });

    denyBtn.addEventListener("click", function () {
      if (resolved) return;
      resolved = true;
      wrapper.remove();
      tools.forEach(function (t) {
        if (toolCards[t.id]) updateCardStatus(toolCards[t.id], "denied");
      });
      fetch("/api/tool-approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId, denied_ids: tools.map(function (t) { return t.id; }) }),
      });
    });

    wrapper.appendChild(approveBtn);
    wrapper.appendChild(denyBtn);
    stream.appendChild(wrapper);
  }

  function syncConvId(conv, serverId) {
    var oldId = conv.id;
    if (oldId !== serverId) {
      conv.id = serverId;
      conversations.forEach(function (c) { if (c.id === oldId) c.id = serverId; });
      if (activeConversationId === oldId) activeConversationId = serverId;
    }
    conv.hasServerId = true;
    renderConversations();
  }

  var acDebounce = null;

  function getPathCompletionStart(val, cursorPos) {
    var i = cursorPos - 1;
    while (i >= 0 && !/\s/.test(val[i])) {
      i--;
    }
    var tokenStart = i + 1;
    if (tokenStart >= cursorPos) return -1;
    if (val[tokenStart] !== "/") return -1;
    return tokenStart;
  }

  function showAutocomplete(entries, pathStart) {
    acEntries = entries;
    acSelectedIdx = -1;
    acDropdown.innerHTML = "";
    if (!entries.length) { hideAutocomplete(); return; }

    entries.forEach(function (entry, idx) {
      var div = document.createElement("div");
      div.className = "ac-item";
      div.innerHTML =
        '<span class="ac-icon ' + (entry.type === "directory" ? "dir" : "file") + '">' +
        (entry.type === "directory" ? "&#128193;" : "&#128196;") + '</span>' +
        '<span class="ac-name">' + escapeHtml(entry.name) + '</span>';
      div.addEventListener("mousedown", function (e) {
        e.preventDefault();
        insertAutocomplete(entry, pathStart);
      });
      acDropdown.appendChild(div);
    });

    acDropdown.classList.add("visible");
    acVisible = true;
  }

  function hideAutocomplete() {
    acDropdown.classList.remove("visible");
    acVisible = false;
    acEntries = [];
    acSelectedIdx = -1;
  }

  function insertAutocomplete(entry, pathStart) {
    var val = chatInput.value;
    var cursorPos = chatInput.selectionStart;
    var before = val.slice(0, pathStart);
    var after = val.slice(cursorPos);
    var insertPath = entry.path;
    if (entry.type === "directory") insertPath += "/";
    chatInput.value = before + insertPath + after;
    chatInput.selectionStart = chatInput.selectionEnd = before.length + insertPath.length;
    chatInput.focus();
    hideAutocomplete();

    if (entry.type === "directory") {
      fetchAutocomplete(insertPath);
    }
  }

  function fetchAutocomplete(pathQuery) {
    clearTimeout(acDebounce);
    acDebounce = setTimeout(function () {
      fetch("/api/files/list?path=" + encodeURIComponent(pathQuery))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.entries && data.entries.length > 0) {
            var val = chatInput.value;
            var cursorPos = chatInput.selectionStart;
            var ps = getPathCompletionStart(val, cursorPos);
            if (ps >= 0) {
              showAutocomplete(data.entries, ps);
            } else {
              hideAutocomplete();
            }
          } else {
            hideAutocomplete();
          }
        })
        .catch(function () { hideAutocomplete(); });
    }, 150);
  }

  chatInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 200) + "px";

    var val = this.value;
    var cursorPos = this.selectionStart;

    var pathStart = getPathCompletionStart(val, cursorPos);
    if (pathStart >= 0) {
      var pathQuery = val.slice(pathStart, cursorPos);
      fetchAutocomplete(pathQuery);
      return;
    }
    hideAutocomplete();
  });

  chatInput.addEventListener("keydown", function (e) {
    if (acVisible) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        acSelectedIdx = Math.min(acSelectedIdx + 1, acEntries.length - 1);
        highlightAcItem();
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        acSelectedIdx = Math.max(acSelectedIdx - 1, 0);
        highlightAcItem();
        return;
      }
      if (e.key === "Tab" || e.key === "Enter") {
        if (acSelectedIdx >= 0 && acSelectedIdx < acEntries.length) {
          e.preventDefault();
          var val = chatInput.value;
          var cursorPos = chatInput.selectionStart;
          var ps = getPathCompletionStart(val, cursorPos);
          insertAutocomplete(acEntries[acSelectedIdx], ps >= 0 ? ps : cursorPos);
          return;
        }
        if (e.key === "Tab") { e.preventDefault(); hideAutocomplete(); return; }
      }
      if (e.key === "Escape") { e.preventDefault(); hideAutocomplete(); return; }
    }

    if (e.key === "Enter" && !e.shiftKey && !acVisible) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  chatInput.addEventListener("blur", function () {
    setTimeout(hideAutocomplete, 200);
  });

  function highlightAcItem() {
    var items = acDropdown.querySelectorAll(".ac-item");
    items.forEach(function (item, idx) {
      item.classList.toggle("selected", idx === acSelectedIdx);
    });
    if (acSelectedIdx >= 0 && items[acSelectedIdx]) {
      items[acSelectedIdx].scrollIntoView({ block: "nearest" });
    }
  }

  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();
    if (isStreaming) { if (abortController) abortController.abort(); return; }
    var text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = "";
    chatInput.style.height = "auto";
    hideAutocomplete();
    sendMessage(text);
  });

  newChatBtn.addEventListener("click", function () { newConversation(); });

  if (modeSelect) {
    modeSelect.addEventListener("change", applyChatModePlaceholder);
  }
  applyChatModePlaceholder();

  if (themeToggle) {
    themeToggle.addEventListener("click", toggleTheme);
  }
  if (deleteModalCancel) {
    deleteModalCancel.addEventListener("click", closeDeleteModal);
  }
  if (deleteModalConfirm) {
    deleteModalConfirm.addEventListener("click", function () {
      confirmDeleteConversation();
    });
  }
  if (deleteModal) {
    deleteModal.addEventListener("click", function (e) {
      if (e.target === deleteModal) closeDeleteModal();
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && deleteModal && !deleteModal.classList.contains("hidden")) {
      closeDeleteModal();
    }
  });

  async function autoSelectModel() {
    try {
      var resp = await fetch("/health");
      if (!resp.ok) return;
      var data = await resp.json();
      var keys = data.api_keys_configured || {};
      if (!keys.anthropic && keys.openai) {
        var defaults = data.default_models || {};
        var m = defaults.openai || "gpt-4o-mini";
        var opt = modelSelect.querySelector('option[value="' + m + '"]');
        if (opt) modelSelect.value = m;
      }
    } catch (e) {}
  }

  async function loadConversations() {
    try {
      var resp = await fetch("/api/conversations");
      if (resp.ok) {
        var data = await resp.json();
        if (data.length > 0) {
          conversations = data.map(function (c) {
            return { id: c.id, title: c.title, hasServerId: true, uiMessages: [] };
          });
        }
      }
    } catch (e) {}
    if (conversations.length === 0) { await newConversation(); }
    else { activeConversationId = conversations[0].id; renderConversations(); switchConversation(activeConversationId); }
  }

  autoSelectModel();
  loadConversations();
})();
