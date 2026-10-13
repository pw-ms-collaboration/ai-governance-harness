"use strict";

const form = document.querySelector("#chat-form");
const input = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-button");
const messagesElement = document.querySelector("#messages");
const activityStatus = document.querySelector("#activity-status");
const errorMessage = document.querySelector("#error-message");
const characterCount = document.querySelector("#character-count");
const clearButton = document.querySelector("#clear-chat");
const connection = document.querySelector(".connection");
const connectionStatus = document.querySelector("#connection-status");

let history = [];

function addMessage(role, content) {
  const item = document.createElement("li");
  item.className = `message ${role}`;

  const article = document.createElement("article");
  const heading = document.createElement("h3");
  const body = document.createElement("p");

  heading.textContent = role === "user" ? "You" : "Assistant";
  body.textContent = content;
  article.append(heading, body);
  item.append(article);
  messagesElement.append(item);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function setBusy(isBusy) {
  input.disabled = isBusy;
  sendButton.disabled = isBusy;
  activityStatus.textContent = isBusy ? "Thinking and checking governance tools" : "";
  activityStatus.classList.toggle("busy", isBusy);
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
}

async function checkHealth() {
  try {
    const response = await fetch("/health/ready", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("not ready");
    }
    connection.classList.add("ready");
    connection.classList.remove("error");
    connectionStatus.textContent = "Chat service ready";
  } catch {
    connection.classList.add("error");
    connection.classList.remove("ready");
    connectionStatus.textContent = "Chat service unavailable";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  const content = input.value.trim();
  if (!content) {
    showError("Enter a message before sending.");
    input.focus();
    return;
  }

  addMessage("user", content);
  history.push({ role: "user", content });
  history = history.slice(-20);
  input.value = "";
  characterCount.textContent = "0 / 4000";
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "The chat request failed.");
    }
    addMessage("assistant", payload.message);
    history.push({ role: "assistant", content: payload.message });
    history = history.slice(-20);
  } catch (error) {
    showError(error.message || "The chat service could not be reached.");
  } finally {
    setBusy(false);
    input.focus();
  }
});

input.addEventListener("input", () => {
  characterCount.textContent = `${input.value.length} / 4000`;
});

input.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key === "Enter") {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.question || "";
    characterCount.textContent = `${input.value.length} / 4000`;
    input.focus();
  });
});

clearButton.addEventListener("click", () => {
  history = [];
  messagesElement.replaceChildren();
  addMessage(
    "assistant",
    "Conversation cleared. Ask about a synthetic member, churn risk, or FUM outflow.",
  );
  clearError();
  input.focus();
});

checkHealth();
