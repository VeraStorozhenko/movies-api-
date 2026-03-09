const authView = document.getElementById("authView");
const chatView = document.getElementById("chatView");
const authStatus = document.getElementById("authStatus");
const authHint = document.getElementById("authHint");
const userBadge = document.getElementById("userBadge");

const log = document.getElementById("log");
const usersList = document.getElementById("users");
const userSuggestions = document.getElementById("userSuggestions");

const roomInput = document.getElementById("room");
const toInput = document.getElementById("to");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("sendBtn");

const authUserInput = document.getElementById("authUser");
const authPassInput = document.getElementById("authPass");
const togglePassBtn = document.getElementById("togglePassBtn");
const registerBtn = document.getElementById("registerBtn");
const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");

const protocol = location.protocol === "https:" ? "wss" : "ws";
let ws = null;
let token = localStorage.getItem("chat_token") || "";
let refreshToken = localStorage.getItem("chat_refresh_token") || "";
let currentUser = localStorage.getItem("chat_user") || "";

function showAuth(message = "Not authenticated") {
  authView.classList.remove("hidden");
  chatView.classList.add("hidden");
  authStatus.textContent = message;
  authHint.textContent = "";
}

function showChat() {
  authView.classList.add("hidden");
  chatView.classList.remove("hidden");
  userBadge.textContent = `Logged in as ${currentUser}`;
  authHint.textContent = "";
}

function authHeaders() {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function addMessage(entry) {
  const li = document.createElement("li");
  const timestamp = entry.created_at ? new Date(entry.created_at).toLocaleTimeString() : "";
  const visibility = entry.recipient ? ` (private to ${entry.recipient})` : "";
  li.textContent = `${timestamp} ${entry.sender}${visibility}: ${entry.text}`.trim();
  log.appendChild(li);
}

function renderPresence(users) {
  usersList.innerHTML = "";
  userSuggestions.innerHTML = "";

  users.forEach((name) => {
    const li = document.createElement("li");
    li.textContent = name;
    usersList.appendChild(li);

    const option = document.createElement("option");
    option.value = name;
    userSuggestions.appendChild(option);
  });
}

async function refreshAccessToken() {
  if (!refreshToken) return false;

  const response = await fetch("/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) return false;

  const data = await response.json();
  token = data.access_token;
  currentUser = data.username;
  localStorage.setItem("chat_token", token);
  localStorage.setItem("chat_user", currentUser);
  return true;
}

function setAuthHint(message = "") {
  authHint.textContent = message;
}

function validateCredentials(username, password) {
  if (!username) return "Enter username.";
  if (username.length < 3) return "Username must be at least 3 characters.";
  if (username.length > 32) return "Username must be at most 32 characters.";
  if (!password) return "Enter password.";
  if (password.length < 6) return "Password is too short: minimum 6 characters.";
  if (password.length > 128) return "Password is too long: maximum 128 characters.";
  return "";
}

function parseErrorMessage(data, fallback) {
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail) && data.detail.length > 0) {
    const first = data.detail[0];
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "field";
    return `${field}: ${first.msg}`;
  }
  return fallback;
}

async function authFetch(url, options = {}) {
  let response = await fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() },
  });

  if (response.status !== 401) return response;

  const refreshed = await refreshAccessToken();
  if (!refreshed) return response;

  response = await fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() },
  });
  return response;
}

async function loadHistory() {
  const room = roomInput.value || "general";
  const response = await authFetch(`/history/${encodeURIComponent(room)}?limit=100`);
  if (!response.ok) return;

  log.innerHTML = "";
  const data = await response.json();
  (Array.isArray(data.messages) ? data.messages : []).forEach(addMessage);
}

function connectSocket() {
  if (!token) return;
  if (ws && ws.readyState <= WebSocket.OPEN) ws.close();

  const room = roomInput.value || "general";
  ws = new WebSocket(`${protocol}://${location.host}/ws/${room}?token=${encodeURIComponent(token)}`);

  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload?.type === "presence") {
        renderPresence(Array.isArray(payload.users) ? payload.users : []);
        return;
      }
      if (payload?.type === "message") {
        addMessage(payload);
        return;
      }
    } catch (_err) {
      // Ignore malformed frames.
    }

    addMessage({ sender: "system", text: event.data, created_at: null });
  };

  ws.onclose = () => {
    if (chatView.classList.contains("hidden")) return;
    renderPresence([]);
  };
}

async function register() {
  const username = authUserInput.value.trim();
  const password = authPassInput.value;
  const validationError = validateCredentials(username, password);
  if (validationError) {
    setAuthHint(validationError);
    return;
  }

  const response = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (response.ok) {
    authStatus.textContent = "Registered. Now login.";
    setAuthHint("");
    return;
  }

  const data = await response.json().catch(() => ({}));
  setAuthHint(parseErrorMessage(data, "Registration failed"));
}

async function login() {
  const username = authUserInput.value.trim();
  const password = authPassInput.value;
  const validationError = validateCredentials(username, password);
  if (validationError) {
    setAuthHint(validationError);
    return;
  }

  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    authStatus.textContent = "Login failed";
    const data = await response.json().catch(() => ({}));
    setAuthHint(parseErrorMessage(data, "Login failed"));
    return;
  }

  const data = await response.json();
  token = data.access_token;
  refreshToken = data.refresh_token;
  currentUser = data.username;
  localStorage.setItem("chat_token", token);
  localStorage.setItem("chat_refresh_token", refreshToken);
  localStorage.setItem("chat_user", currentUser);
  setAuthHint("");

  showChat();
  connectSocket();
  await loadHistory();
}

async function logout() {
  if (token || refreshToken) {
    await fetch("/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ refresh_token: refreshToken || null }),
    });
  }

  if (ws && ws.readyState <= WebSocket.OPEN) ws.close();
  ws = null;

  token = "";
  refreshToken = "";
  currentUser = "";
  localStorage.removeItem("chat_token");
  localStorage.removeItem("chat_refresh_token");
  localStorage.removeItem("chat_user");

  renderPresence([]);
  log.innerHTML = "";
  toInput.value = "";
  msgInput.value = "";
  showAuth("Not authenticated");
}

function sendMsg() {
  const msg = msgInput.value || "";
  const to = toInput.value.trim();
  if (!msg || !ws || ws.readyState !== WebSocket.OPEN) return;

  ws.send(JSON.stringify({ msg, to: to || null }));
  msgInput.value = "";
}

registerBtn.addEventListener("click", register);
loginBtn.addEventListener("click", login);
logoutBtn.addEventListener("click", logout);
togglePassBtn.addEventListener("click", () => {
  const isPassword = authPassInput.type === "password";
  authPassInput.type = isPassword ? "text" : "password";
  togglePassBtn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
});
sendBtn.addEventListener("click", sendMsg);
msgInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") sendMsg();
});
roomInput.addEventListener("change", async () => {
  if (!token) return;
  connectSocket();
  await loadHistory();
});

(async () => {
  if (!token || !currentUser) {
    showAuth();
    return;
  }

  const refreshed = await refreshAccessToken();
  if (!refreshed) {
    await logout();
    return;
  }

  showChat();
  connectSocket();
  await loadHistory();
})();
