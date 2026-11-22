/**
 * CONATACOCH · App móvil Fase 3
 * Negro #0B0B0B · Blanco #FFFFFF · Amarillo #FFD100
 *
 * Consume los endpoints reales de Fase 2 y los endpoints aditivos de Fase 3.
 * Sin frameworks: fetch + Leaflet + QRCode + Web Audio.
 */
(() => {
  "use strict";

  const API = "/api";
  const STORAGE_KEY = "conatacoch.session.v3";
  const PAGE_SIZE = 10;
  const ROLE_LABEL = {
    ADMIN: "Administrador",
    CONDUCTOR: "Conductor",
    CLIENTE: "Pasajero",
  };
  const DEMO = {
    pasajero: {
      email: "pasajero1@conatacoch.cl",
      password: "Pasajero2026!",
      hint: "Demo pasajero: pasajero1@conatacoch.cl · Pasajero2026!",
    },
    conductor: {
      email: "conductor1@conatacoch.cl",
      password: "Conduc2026!",
      hint: "Demo conductor: conductor1@conatacoch.cl · Conduc2026!",
    },
    admin: {
      email: "admin@conatacoch.cl",
      password: "AdminConata2026!",
      hint: "Demo admin: admin@conatacoch.cl · AdminConata2026!",
    },
  };

  const ICONS = {
    route:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19c2.5 0 2.5-14 7-14s4.5 14 7 14" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/><circle cx="5" cy="19" r="1.8" fill="currentColor"/><circle cx="19" cy="19" r="1.8" fill="currentColor"/></svg>',
    car:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 15l1.6-4.6A3 3 0 0 1 8.4 8h7.2a3 3 0 0 1 2.8 2.4L20 15" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/><rect x="3" y="14" width="18" height="5.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.9"/><circle cx="7.5" cy="19.5" r="1.4" fill="currentColor"/><circle cx="16.5" cy="19.5" r="1.4" fill="currentColor"/></svg>',
    grid:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="6.5" height="6.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.9"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.9"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.9"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.9"/></svg>',
    user:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.4" fill="none" stroke="currentColor" stroke-width="1.9"/><path d="M5 20c.8-3.4 3.5-5.2 7-5.2s6.2 1.8 7 5.2" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
  };

  const $ = (id) => document.getElementById(id);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const fmt = new Intl.NumberFormat("es-CL");
  const clp = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  });

  class ApiError extends Error {
    constructor(message, status = 0, data = {}) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.data = data;
    }
  }

  const state = {
    session: null,
    role: null,
    currentView: null,
    lineasCatalogo: [],
    routeResults: [],
    selectedRoute: null,
    selectedLinea: null,
    lineasApiCache: new Map(),
    paraderos: [],
    fleet: [],
    eta: null,
    passengerLocation: null,
    passengerMap: null,
    passengerLayer: null,
    passengerMapFitted: false,
    adminMap: null,
    adminLayer: null,
    adminMapFitted: false,
    adminFleet: [],
    conductor: null,
    shiftActive: false,
    cupos: 4,
    gpsTimer: null,
    gpsSending: false,
    gpsSim: null,
    pendingPagos: [],
    pendingInitialized: false,
    seenPagos: new Set(),
    paymentAlertPago: null,
    qrPolling: null,
    qrActual: null,
    otp: { action: null, codigo: null },
    timers: {},
    admin: {
      subview: "conductores",
      conductores: [],
      conductoresPage: 1,
      conductoresTotal: 0,
      conductoresSearch: "",
      lineas: [],
      lineasPage: 1,
      lineasTotal: 0,
      lineasSearch: "",
      lineaOptions: null,
      pagos: [],
      pagosPage: 1,
      pagosTotal: 0,
      pagosEstado: "",
      conductorEditId: null,
      lineaEditId: null,
    },
  };

  // ------------------------------------------------------------------ Utils
  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[ch]));

  const normalize = (value) =>
    String(value ?? "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();

  const setText = (id, value) => {
    const el = $(id);
    if (el) el.textContent = value;
  };

  const setError = (id, message = "") => {
    const el = $(id);
    if (el) el.textContent = message;
  };

  const formatDate = (value) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleString("es-CL", { dateStyle: "short", timeStyle: "short" });
  };

  const relativeAge = (seconds) => {
    if (seconds === null || seconds === undefined) return "sin telemetría";
    if (seconds < 60) return `hace ${seconds}s`;
    if (seconds < 3600) return `hace ${Math.floor(seconds / 60)}m`;
    return `hace ${Math.floor(seconds / 3600)}h`;
  };

  let toastTimer;
  function toast(message) {
    const el = $("toast");
    if (!el) return;
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
  }

  function errorMessage(error) {
    if (!error) return "Error inesperado.";
    if (error instanceof ApiError) {
      const data = error.data || {};
      const detail = data.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) return detail.join(" ");
      if (detail && typeof detail === "object") {
        const parts = Object.entries(detail).map(([key, value]) => {
          const text = Array.isArray(value) ? value.join(", ") : String(value);
          return `${key}: ${text}`;
        });
        return parts.join(" · ") || error.message;
      }
      if (typeof data.error === "string") return data.error.replace(/_/g, " ");
      return error.message;
    }
    return error.message || String(error);
  }

  // --------------------------------------------------------------- Session
  function loadStoredSession() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (!data || !data.access || !data.usuario) return null;
      return data;
    } catch {
      return null;
    }
  }

  function saveSession() {
    try {
      if (state.session) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state.session));
      }
    } catch {
      /* almacenamiento no disponible */
    }
  }

  function clearStoredSession() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* noop */
    }
  }

  async function refreshSession() {
    if (!state.session?.refresh) return false;
    try {
      const response = await fetch(`${API}/auth/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh: state.session.refresh }),
      });
      if (!response.ok) return false;
      const data = await response.json();
      if (!data.access) return false;
      state.session.access = data.access;
      saveSession();
      return true;
    } catch {
      return false;
    }
  }

  async function api(path, options = {}) {
    const {
      method = "GET",
      body,
      auth = true,
      retry = true,
      timeout = 15000,
    } = options;

    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth && state.session?.access) {
      headers.Authorization = `Bearer ${state.session.access}`;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    let response;
    try {
      response = await fetch(API + path, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } catch {
      clearTimeout(timer);
      throw new ApiError("No se pudo conectar con la API.", 0, {});
    }
    clearTimeout(timer);

    if (response.status === 401 && auth && retry && state.session?.refresh) {
      const refreshed = await refreshSession();
      if (refreshed) {
        return api(path, { ...options, retry: false });
      }
      logout();
      throw new ApiError("La sesión expiró. Inicia sesión nuevamente.", 401, {});
    }

    const text = await response.text();
    let data = {};
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }
    }

    if (!response.ok) {
      throw new ApiError(errorMessage(new ApiError("", response.status, data)), response.status, data);
    }
    return data;
  }

  function normalizeNext(next) {
    if (!next) return null;
    try {
      const url = new URL(next, window.location.origin);
      return url.pathname.replace(/^\/api/, "") + url.search;
    } catch {
      return null;
    }
  }

  async function fetchAll(path, maxPages = 12) {
    let next = path;
    let page = 0;
    const out = [];
    while (next && page < maxPages) {
      const data = await api(next);
      if (Array.isArray(data)) return data;
      out.push(...(data.results || []));
      next = normalizeNext(data.next);
      page += 1;
    }
    return out;
  }

  // ------------------------------------------------------------------ Login
  async function checkApi() {
    const dot = $("login-api-dot");
    const text = $("login-api-text");
    if (!dot || !text) return;
    try {
      const response = await fetch(`${API}/health/live/`, {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) throw new Error();
      dot.classList.add("is-ok");
      dot.classList.remove("is-err");
      text.textContent = "API operativa";
    } catch {
      dot.classList.add("is-err");
      dot.classList.remove("is-ok");
      text.textContent = "API no disponible";
    }
  }

  function showLogin() {
    const app = $("screen-app");
    const login = $("screen-login");
    if (app) app.hidden = true;
    if (login) login.hidden = false;
    const password = $("login-password");
    if (password) password.value = "";
    checkApi();
  }

  function enterApp() {
    if (!state.session?.usuario) {
      showLogin();
      return;
    }
    state.role = state.session.usuario.rol;
    const app = $("screen-app");
    const login = $("screen-login");
    if (login) login.hidden = true;
    if (app) app.hidden = false;
    setText("header-role", ROLE_LABEL[state.role] || state.role);
    setText("role-chip", state.role);
    renderAccount();
    buildTabs();
    switchView(defaultViewForRole());
  }

  function defaultViewForRole() {
    if (state.role === "CONDUCTOR") return "conductor";
    if (state.role === "ADMIN") return "admin";
    return "pasajero";
  }

  function logout() {
    stopAllTimers();
    stopGps();
    closeAllModals();
    clearStoredSession();
    state.session = null;
    state.role = null;
    state.currentView = null;
    state.selectedRoute = null;
    state.selectedLinea = null;
    state.fleet = [];
    state.eta = null;
    state.conductor = null;
    state.shiftActive = false;
    state.pendingPagos = [];
    state.seenPagos.clear();
    state.pendingInitialized = false;
    state.qrActual = null;
    state.paymentAlertPago = null;
    showLogin();
    toast("Sesión cerrada");
  }

  async function handleLogin(event) {
    event.preventDefault();
    setError("login-error", "");
    const email = $("login-email").value.trim();
    const password = $("login-password").value;
    if (!email || !password) {
      setError("login-error", "Ingresa tu email y contraseña.");
      return;
    }

    const button = $("login-submit");
    button.disabled = true;
    button.textContent = "Entrando…";
    try {
      const data = await api("/auth/login/", {
        method: "POST",
        body: { email, password },
        auth: false,
      });
      state.session = {
        access: data.access,
        refresh: data.refresh,
        usuario: data.usuario,
      };
      saveSession();
      toast(`Bienvenido, ${data.usuario.nombre}`);
      enterApp();
    } catch (error) {
      setError("login-error", errorMessage(error));
    } finally {
      button.disabled = false;
      button.textContent = "Entrar";
    }
  }

  function bindLogin() {
    $("login-form")?.addEventListener("submit", handleLogin);
    $("toggle-password")?.addEventListener("click", () => {
      const input = $("login-password");
      if (!input) return;
      const visible = input.type === "text";
      input.type = visible ? "password" : "text";
      $("toggle-password").textContent = visible ? "Ver" : "Ocultar";
    });
    $$("[data-demo]").forEach((button) => {
      button.addEventListener("click", () => {
        const demo = DEMO[button.dataset.demo];
        if (!demo) return;
        $("login-email").value = demo.email;
        $("login-password").value = demo.password;
        setText("demo-hint", demo.hint);
        setError("login-error", "");
        $("login-submit")?.focus();
      });
    });
  }

  // ------------------------------------------------------------- Navigation
  function buildTabs() {
    const tabs = [];
    if (state.role === "CLIENTE") {
      tabs.push({ id: "pasajero", label: "Pasajero", icon: ICONS.route });
    } else if (state.role === "CONDUCTOR") {
      tabs.push({ id: "conductor", label: "Conducir", icon: ICONS.car });
    } else if (state.role === "ADMIN") {
      tabs.push({ id: "admin", label: "Admin", icon: ICONS.grid });
    }
    tabs.push({ id: "cuenta", label: "Cuenta", icon: ICONS.user });

    const tabbar = $("tabbar");
    if (!tabbar) return;
    tabbar.innerHTML = tabs
      .map(
        (tab) => `<button class="tab" type="button" data-view="${tab.id}">
          ${tab.icon}<span>${esc(tab.label)}</span>
        </button>`
      )
      .join("");
  }

  function switchView(name) {
    if (!name) return;
    state.currentView = name;
    $$(".view").forEach((view) => {
      view.classList.toggle("is-active", view.dataset.view === name);
    });
    $$(".tab").forEach((tab) => {
      const active = tab.dataset.view === name;
      tab.classList.toggle("is-active", active);
      if (active) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    });
    const main = $("app-main");
    if (main) main.scrollTop = 0;

    if (name === "pasajero") {
      loadCatalogo();
      initPassengerMap();
      if (state.selectedLinea) {
        loadFleet(state.selectedLinea.id);
        calcularEta();
      }
      setTimeout(() => state.passengerMap?.invalidateSize(), 90);
    } else if (name === "conductor") {
      loadConductorProfile();
    } else if (name === "admin") {
      loadAdminStats();
      loadAdminSubview(state.admin.subview);
    } else if (name === "cuenta") {
      renderAccount();
    }
    setViewTimers(name);
  }

  function stopAllTimers() {
    Object.values(state.timers).forEach((timer) => clearInterval(timer));
    state.timers = {};
  }

  function setViewTimers(view) {
    stopAllTimers();
    if (view === "pasajero" && state.selectedLinea) {
      state.timers.passenger = setInterval(() => {
        if (state.currentView !== "pasajero" || !state.selectedLinea) return;
        loadFleet(state.selectedLinea.id).catch(() => {});
        calcularEta();
      }, 10000);
    }
    if (view === "conductor" && state.shiftActive) {
      state.timers.pending = setInterval(pollPendingPagos, 5000);
    }
    if (view === "admin") {
      if (state.admin.subview === "flota") {
        state.timers.adminFleet = setInterval(() => {
          if (state.currentView === "admin" && state.admin.subview === "flota") {
            loadAdminFlota();
          }
        }, 8000);
      }
      if (state.admin.subview === "pagos") {
        state.timers.adminPagos = setInterval(() => {
          if (state.currentView === "admin" && state.admin.subview === "pagos") {
            loadPagos(state.admin.pagosPage, state.admin.pagosEstado, true);
          }
        }, 12000);
      }
    }
  }

  function bindAppEvents() {
    $("tabbar")?.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-view]");
      if (tab) switchView(tab.dataset.view);
    });
    $("brand-home")?.addEventListener("click", () => switchView(defaultViewForRole()));
    $("logout-btn")?.addEventListener("click", logout);
    $("account-logout")?.addEventListener("click", logout);

    // Pasajero
    let routeTimer;
    $("route-search")?.addEventListener("input", (event) => {
      clearTimeout(routeTimer);
      routeTimer = setTimeout(() => renderRouteResults(event.target.value), 120);
    });
    $("route-results")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-route-index]");
      if (!button) return;
      const row = state.routeResults[Number(button.dataset.routeIndex)];
      if (row) selectRoute(row);
    });
    $("passenger-refresh")?.addEventListener("click", () => {
      if (state.selectedLinea) refreshPassengerData(false);
      else loadCatalogo();
      toast("Datos actualizados");
    });
    $("locate-btn")?.addEventListener("click", locatePassenger);
    $("pay-btn")?.addEventListener("click", openQrModal);

    // Conductor
    $("shift-btn")?.addEventListener("click", handleShift);
    $("gps-btn")?.addEventListener("click", toggleGps);
    $("seat-available")?.addEventListener("click", () => setCupos(state.conductor?.capacidad_pasajeros || 4));
    $("seat-full")?.addEventListener("click", () => setCupos(0));
    $("cupos-minus")?.addEventListener("click", () => setCupos(state.cupos - 1));
    $("cupos-plus")?.addEventListener("click", () => setCupos(state.cupos + 1));
    $("payment-alert-confirm")?.addEventListener("click", () => {
      if (state.paymentAlertPago) confirmPago(state.paymentAlertPago.codigo_qr_uuid);
    });
    $$("[data-dismiss]").forEach((button) => {
      button.addEventListener("click", () => {
        const id = button.dataset.dismiss;
        const el = $(id);
        if (el) el.hidden = true;
      });
    });

    // Admin
    $("admin-refresh")?.addEventListener("click", () => {
      loadAdminStats();
      loadAdminSubview(state.admin.subview);
      toast("Panel actualizado");
    });
    $("admin-subtabs")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-admin]");
      if (button) loadAdminSubview(button.dataset.admin);
    });
    $("new-conductor-btn")?.addEventListener("click", () => openConductorForm(null));
    $("conductor-cancel")?.addEventListener("click", () => {
      $("conductor-form").hidden = true;
      state.admin.conductorEditId = null;
    });
    $("conductor-form")?.addEventListener("submit", handleConductorSubmit);
    $("conductor-search-btn")?.addEventListener("click", () => {
      state.admin.conductoresSearch = $("conductor-search").value.trim();
      loadConductores(1, state.admin.conductoresSearch);
    });
    $("conductor-search")?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      state.admin.conductoresSearch = event.target.value.trim();
      loadConductores(1, state.admin.conductoresSearch);
    });
    $("admin-conductores-list")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const id = Number(button.dataset.id);
      if (button.dataset.action === "edit-conductor") openConductorForm(id);
      if (button.dataset.action === "delete-conductor") deleteConductor(id);
    });

    $("new-linea-btn")?.addEventListener("click", () => openLineaForm(null));
    $("linea-cancel")?.addEventListener("click", () => {
      $("linea-form").hidden = true;
      state.admin.lineaEditId = null;
    });
    $("linea-form")?.addEventListener("submit", handleLineaSubmit);
    $("linea-search-btn")?.addEventListener("click", () => {
      state.admin.lineasSearch = $("linea-search").value.trim();
      loadLineas(1, state.admin.lineasSearch);
    });
    $("linea-search")?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      state.admin.lineasSearch = event.target.value.trim();
      loadLineas(1, state.admin.lineasSearch);
    });
    $("admin-lineas-list")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const id = Number(button.dataset.id);
      if (button.dataset.action === "edit-linea") openLineaForm(id);
      if (button.dataset.action === "save-tarifa") saveTarifa(id);
    });
    $("pago-estado")?.addEventListener("change", (event) => {
      state.admin.pagosEstado = event.target.value;
      loadPagos(1, state.admin.pagosEstado);
    });

    bindPager("conductores-pager", (direction) => {
      const page = state.admin.conductoresPage + (direction === "next" ? 1 : -1);
      if (page < 1) return;
      loadConductores(page, state.admin.conductoresSearch);
    });
    bindPager("lineas-pager", (direction) => {
      const page = state.admin.lineasPage + (direction === "next" ? 1 : -1);
      if (page < 1) return;
      loadLineas(page, state.admin.lineasSearch);
    });
    bindPager("pagos-pager", (direction) => {
      const page = state.admin.pagosPage + (direction === "next" ? 1 : -1);
      if (page < 1) return;
      loadPagos(page, state.admin.pagosEstado);
    });

    // Modales y OTP / QR
    $("otp-form")?.addEventListener("submit", handleOtpSubmit);
    $("qr-form")?.addEventListener("submit", handleQrSubmit);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeAllModals();
    });
  }

  function bindPager(id, handler) {
    const pager = $(id);
    if (!pager) return;
    pager.addEventListener("click", (event) => {
      const button = event.target.closest("[data-page]");
      if (!button || button.disabled) return;
      handler(button.dataset.page);
    });
  }

  function renderPager(labelId, page, total, pageSize = PAGE_SIZE) {
    const label = $(labelId);
    if (!label) return;
    const pages = Math.max(1, Math.ceil((total || 0) / pageSize));
    label.textContent = `${page} / ${pages}`;
    const pager = label.parentElement;
    if (!pager) return;
    const prev = pager.querySelector('[data-page="prev"]');
    const next = pager.querySelector('[data-page="next"]');
    if (prev) prev.disabled = page <= 1;
    if (next) next.disabled = page >= pages;
  }

  // -------------------------------------------------------------- Catálogo
  async function loadCatalogo() {
    if (state.lineasCatalogo.length) {
      renderRouteResults($("route-search")?.value || "");
      return;
    }
    try {
      const response = await fetch("assets/recorridos_conatacoch.json", { cache: "no-store" });
      if (!response.ok) throw new Error();
      const data = await response.json();
      state.lineasCatalogo = Array.isArray(data) ? data : [];
      setText(
        "route-source",
        `Catálogo oficial · ${fmt.format(state.lineasCatalogo.length)} itinerarios`
      );
      renderRouteResults("");
    } catch {
      setText("route-source", "No se pudo cargar el catálogo local. Revisa assets/.");
    }
  }

  function renderRouteResults(query) {
    const q = normalize(query);
    const results = state.lineasCatalogo
      .filter((row) => {
        if (!q) return true;
        return normalize(
          `${row.FOLIO} ${row.NOMBRE_RECORRIDO} ${row.COMUNA_ORIGEN} ${row.COMUNA_DESTINO} ${row.DOMICILIO_ORIGEN} ${row.DOMICILIO_DESTINO}`
        ).includes(q);
      })
      .slice(0, 40);

    state.routeResults = results;
    const container = $("route-results");
    if (!container) return;
    if (!results.length) {
      container.innerHTML = '<p class="empty">Sin coincidencias.</p>';
      return;
    }
    container.innerHTML = results
      .map(
        (row, index) => `<button class="route-result" type="button" data-route-index="${index}" role="option">
          <span class="folio">#${esc(row.FOLIO)}</span>
          <span>
            <strong>${esc(row.NOMBRE_RECORRIDO)}</strong>
            <small>${esc(row.COMUNA_ORIGEN)} → ${esc(row.COMUNA_DESTINO)} · ${esc(row.TIPO_TRAZADO || "PRINCIPAL")}</small>
          </span>
        </button>`
      )
      .join("");
  }

  function renderSelectedRoute() {
    const row = state.selectedRoute;
    const card = $("selected-route");
    if (!card || !row) return;
    card.hidden = false;
    setText("selected-folio", `#${row.FOLIO}`);
    setText("selected-tipo", row.TIPO_TRAZADO || "PRINCIPAL");
    setText("selected-name", row.NOMBRE_RECORRIDO);
    setText("selected-origen", row.COMUNA_ORIGEN);
    setText("selected-destino", row.COMUNA_DESTINO);
    setText(
      "selected-comunas",
      `${row.DOMICILIO_ORIGEN || "Origen"} → ${row.DOMICILIO_DESTINO || "Destino"}`
    );
    const tarifa = state.selectedLinea
      ? clp.format(Number(state.selectedLinea.tarifa_actual || 0))
      : "Tarifa no informada";
    setText("selected-tarifa", tarifa);
  }

  async function resolveLinea(row) {
    const key = `${row.FOLIO}|${row.NOMBRE_RECORRIDO}|${row.TIPO_TRAZADO || "PRINCIPAL"}`;
    if (state.lineasApiCache.has(key)) return state.lineasApiCache.get(key);

    const data = await api(`/lineas/?folio=${encodeURIComponent(row.FOLIO)}&page_size=100`);
    let match = (data.results || []).find(
      (linea) =>
        String(linea.nombre_recorrido) === String(row.NOMBRE_RECORRIDO) &&
        String(linea.tipo_trazado) === String(row.TIPO_TRAZADO || "PRINCIPAL")
    );
    if (!match) {
      const search = await api(
        `/lineas/?search=${encodeURIComponent(row.NOMBRE_RECORRIDO)}&page_size=100`
      );
      match = (search.results || []).find(
        (linea) =>
          Number(linea.folio) === Number(row.FOLIO) &&
          String(linea.tipo_trazado) === String(row.TIPO_TRAZADO || "PRINCIPAL")
      );
    }
    if (!match) {
      throw new Error("Recorrido no disponible en la API. Ejecuta seed_conatacoch.");
    }
    state.lineasApiCache.set(key, match);
    return match;
  }

  async function selectRoute(row) {
    state.selectedRoute = row;
    state.selectedLinea = null;
    state.eta = null;
    state.paraderos = [];
    state.fleet = [];
    state.passengerMapFitted = false;
    renderSelectedRoute();
    const results = $("route-results");
    if (results) results.innerHTML = "";
    const search = $("route-search");
    if (search) search.value = `${row.FOLIO} · ${row.NOMBRE_RECORRIDO}`;
    setText("eta-badge", "Resolviendo…");
    setText("eta-meta", "Buscando el recorrido en la API…");

    try {
      state.selectedLinea = await resolveLinea(row);
      renderSelectedRoute();
      await refreshPassengerData(true);
      setViewTimers("pasajero");
      toast("Recorrido cargado");
    } catch (error) {
      setText("eta-badge", "No disponible");
      setText("eta-meta", errorMessage(error));
      toast(errorMessage(error));
    }
  }

  // ---------------------------------------------------------------- Mapas
  function initPassengerMap() {
    if (state.passengerMap || !$("passenger-map")) return;
    state.passengerMap = L.map("passenger-map", {
      zoomControl: false,
      attributionControl: true,
    }).setView([-33.4489, -70.6693], 12);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", {
      maxZoom: 19,
      subdomains: "abcd",
      attribution: '&copy; OpenStreetMap &copy; CARTO',
    }).addTo(state.passengerMap);
    L.control.zoom({ position: "bottomright" }).addTo(state.passengerMap);
    state.passengerLayer = L.layerGroup().addTo(state.passengerMap);
  }

  function initAdminMap() {
    if (state.adminMap || !$("admin-map")) return;
    state.adminMap = L.map("admin-map", {
      zoomControl: false,
      attributionControl: true,
    }).setView([-33.4489, -70.6693], 11);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", {
      maxZoom: 19,
      subdomains: "abcd",
      attribution: "&copy; OpenStreetMap &copy; CARTO",
    }).addTo(state.adminMap);
    L.control.zoom({ position: "bottomright" }).addTo(state.adminMap);
    state.adminLayer = L.layerGroup().addTo(state.adminMap);
  }

  function vehicleIcon(patente) {
    const label = String(patente || "TX").slice(-3).toUpperCase();
    return L.divIcon({
      className: "",
      html: `<div class="vehicle-marker">${esc(label)}</div>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
      popupAnchor: [0, -16],
    });
  }

  function paraderoIcon() {
    return L.divIcon({
      className: "",
      html: '<div class="paradero-marker"></div>',
      iconSize: [10, 10],
      iconAnchor: [5, 5],
    });
  }

  function passengerIcon() {
    return L.divIcon({
      className: "",
      html: '<div class="passenger-marker"></div>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
  }

  function updatePassengerMap(fit = false) {
    if (!state.passengerMap || !state.passengerLayer) return;
    state.passengerLayer.clearLayers();
    const points = [];

    state.paraderos.forEach((paradero) => {
      const lat = Number(paradero.latitud);
      const lng = Number(paradero.longitud);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      points.push([lat, lng]);
      L.marker([lat, lng], { icon: paraderoIcon() })
        .addTo(state.passengerLayer)
        .bindPopup(
          `<strong>${esc(paradero.nombre)}</strong><br><small>${esc(paradero.comuna)}</small>`
        );
    });

    if (points.length > 1) {
      L.polyline(points, { color: "#FFD100", weight: 4, opacity: 0.78 }).addTo(
        state.passengerLayer
      );
    }

    state.fleet.forEach((vehiculo) => {
      const lat = Number(vehiculo.latitud);
      const lng = Number(vehiculo.longitud);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      points.push([lat, lng]);
      L.marker([lat, lng], { icon: vehicleIcon(vehiculo.patente) })
        .addTo(state.passengerLayer)
        .bindPopup(
          `<strong>${esc(vehiculo.patente)}</strong><br>${esc(vehiculo.folio_conatacoch)} · ${esc(
            vehiculo.linea_nombre
          )}<br><small>${esc(vehiculo.cupos_disponibles)} cupos · ${Math.round(
            Number(vehiculo.velocidad_kmh || 0)
          )} km/h</small>`
        );
    });

    if (state.passengerLocation) {
      const { lat, lng } = state.passengerLocation;
      points.push([lat, lng]);
      L.marker([lat, lng], { icon: passengerIcon() })
        .addTo(state.passengerLayer)
        .bindPopup("<strong>Tu ubicación</strong>");
    }

    if (fit && points.length) {
      if (points.length === 1) {
        state.passengerMap.setView(points[0], 14);
      } else {
        state.passengerMap.fitBounds(L.latLngBounds(points), {
          padding: [32, 32],
          maxZoom: 15,
        });
      }
      state.passengerMapFitted = true;
    }
  }

  function updateAdminMap(fit = false) {
    if (!state.adminMap || !state.adminLayer) return;
    state.adminLayer.clearLayers();
    const points = [];
    state.adminFleet.forEach((vehiculo) => {
      const lat = Number(vehiculo.latitud);
      const lng = Number(vehiculo.longitud);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      points.push([lat, lng]);
      L.marker([lat, lng], { icon: vehicleIcon(vehiculo.patente) })
        .addTo(state.adminLayer)
        .bindPopup(
          `<strong>${esc(vehiculo.patente)}</strong><br>${esc(
            vehiculo.folio_conatacoch
          )} · ${esc(vehiculo.linea_nombre)}<br><small>${esc(
            vehiculo.cupos_disponibles
          )} cupos · ${relativeAge(vehiculo.edad_segundos)}</small>`
        );
    });
    if (fit && points.length) {
      if (points.length === 1) state.adminMap.setView(points[0], 13);
      else state.adminMap.fitBounds(L.latLngBounds(points), { padding: [30, 30], maxZoom: 13 });
      state.adminMapFitted = true;
    }
  }

  function getBrowserLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocalización no disponible."));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (position) =>
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            aproximada: false,
          }),
        reject,
        { enableHighAccuracy: true, timeout: 6000, maximumAge: 15000 }
      );
    });
  }

  async function ensurePassengerLocation() {
    if (state.passengerLocation) return state.passengerLocation;
    try {
      state.passengerLocation = await getBrowserLocation();
    } catch {
      const base = state.paraderos[0];
      state.passengerLocation = base
        ? {
            lat: Number(base.latitud),
            lng: Number(base.longitud),
            aproximada: true,
          }
        : { lat: -33.4489, lng: -70.6693, aproximada: true };
    }
    return state.passengerLocation;
  }

  async function locatePassenger() {
    try {
      state.passengerLocation = await getBrowserLocation();
      if (state.passengerMap) {
        state.passengerMap.setView(
          [state.passengerLocation.lat, state.passengerLocation.lng],
          15
        );
      }
      updatePassengerMap(false);
      await calcularEta();
      toast("Ubicación actualizada");
    } catch {
      toast("No se pudo obtener tu ubicación. Usando el recorrido.");
    }
  }

  // ------------------------------------------------------------- Pasajero
  async function refreshPassengerData(fit) {
    if (!state.selectedLinea) return;
    const lineaId = state.selectedLinea.id;
    setText("eta-badge", "Actualizando…");
    const [paraderos] = await Promise.allSettled([
      fetchAll(`/paraderos/?linea=${lineaId}&page_size=100`),
      loadFleet(lineaId),
    ]).then((results) => [results[0].status === "fulfilled" ? results[0].value : []]);
    state.paraderos = Array.isArray(paraderos) ? paraderos : [];
    await ensurePassengerLocation();
    await calcularEta();
    updatePassengerMap(fit);
    setViewTimers("pasajero");
  }

  async function loadFleet(lineaId) {
    try {
      const data = await api(`/telemetria/flota/?linea_id=${lineaId}`);
      state.fleet = data.vehiculos || [];
      renderFleet();
      updatePassengerMap(false);
      return state.fleet;
    } catch (error) {
      state.fleet = [];
      renderFleet();
      return [];
    }
  }

  function renderFleet() {
    const list = $("fleet-list");
    setText("fleet-count", fmt.format(state.fleet.length));
    setText("fleet-updated", `Actualizado ${new Date().toLocaleTimeString("es-CL")}`);
    if (!list) return;
    if (!state.fleet.length) {
      list.innerHTML = '<p class="empty">Sin colectivos con telemetría reciente.</p>';
      return;
    }
    list.innerHTML = state.fleet
      .map(
        (vehiculo) => `<article class="fleet-item">
          <span class="fleet-icon">TX</span>
          <span>
            <strong>${esc(vehiculo.patente)}</strong>
            <small>${esc(vehiculo.folio_conatacoch)} · ${esc(
              vehiculo.linea_nombre
            )} · ${relativeAge(vehiculo.edad_segundos)}</small>
          </span>
          <span class="fleet-right">
            <strong>${esc(vehiculo.cupos_disponibles)}</strong>
            <small>cupos · ${Math.round(Number(vehiculo.velocidad_kmh || 0))} km/h</small>
          </span>
        </article>`
      )
      .join("");
  }

  async function calcularEta() {
    if (state.role !== "CLIENTE" || !state.selectedLinea) return;
    await ensurePassengerLocation();
    const location = state.passengerLocation;
    try {
      const data = await api("/eta/calcular/", {
        method: "POST",
        body: {
          linea_id: state.selectedLinea.id,
          latitud_pasajero: location.lat,
          longitud_pasajero: location.lng,
        },
      });
      state.eta = data;
      renderEta(location);
    } catch (error) {
      state.eta = null;
      const message =
        error.status === 404
          ? "No hay conductores en turno para este recorrido."
          : errorMessage(error);
      setText("eta-badge", "Sin ETA");
      setText("eta-value", "—");
      setText("eta-unit", "");
      setText("eta-meta", message);
      setText("eta-options", "");
      const pay = $("pay-btn");
      if (pay) pay.disabled = true;
    }
  }

  function renderEta(location) {
    const nearest = state.eta?.conductor_mas_cercano;
    const options = state.eta?.opciones || [];
    const badge = $("eta-badge");
    if (badge) {
      badge.textContent = nearest ? "En vivo" : "Sin unidades";
      badge.classList.toggle("is-yellow", Boolean(nearest));
    }
    if (!nearest) {
      setText("eta-value", "—");
      setText("eta-unit", "");
      setText(
        "eta-meta",
        "No hay colectivos con telemetría reciente para este recorrido."
      );
      setText("eta-options", "");
      const pay = $("pay-btn");
      if (pay) pay.disabled = true;
      return;
    }

    setText("eta-value", Number(nearest.eta_minutos).toFixed(1));
    setText("eta-unit", "min");
    setText(
      "eta-meta",
      `${nearest.patente} · ${nearest.distancia_km} km · ${nearest.cupos_disponibles} cupos${
        location?.aproximada ? " · ubicación aproximada" : ""
      }`
    );

    const container = $("eta-options");
    if (container) {
      container.innerHTML = options
        .slice(0, 5)
        .map(
          (option) => `<div class="eta-option">
            <span>
              <strong>${esc(option.patente)}</strong>
              <small>${esc(option.folio_conatacoch)} · ${esc(option.cupos_disponibles)} cupos</small>
            </span>
            <span class="eta-option-time">${Number(option.eta_minutos).toFixed(1)} min</span>
          </div>`
        )
        .join("");
    }
    const pay = $("pay-btn");
    if (pay) pay.disabled = false;
  }

  // ------------------------------------------------------------------ QR
  function openQrModal() {
    const nearest = state.eta?.conductor_mas_cercano;
    if (!nearest || !state.selectedLinea) {
      toast("Selecciona un recorrido con colectivos disponibles.");
      return;
    }
    $("qr-form").hidden = false;
    $("qr-result").hidden = true;
    $("qr-canvas").innerHTML = "";
    setError("qr-error", "");
    const monto = $("qr-monto");
    if (monto) {
      monto.value = Math.max(0, Number(state.selectedLinea.tarifa_actual || 1000));
    }
    setText(
      "qr-context",
      `${nearest.patente} · ${nearest.folio_conatacoch} · ${state.selectedLinea.nombre_recorrido}`
    );
    openModal("qr-modal");
  }

  async function handleQrSubmit(event) {
    event.preventDefault();
    setError("qr-error", "");
    const nearest = state.eta?.conductor_mas_cercano;
    if (!nearest || !state.selectedLinea) {
      setError("qr-error", "No hay un colectivo seleccionado.");
      return;
    }
    const monto = Number($("qr-monto").value);
    if (!Number.isFinite(monto) || monto <= 0) {
      setError("qr-error", "Ingresa un monto válido.");
      return;
    }
    const button = $("qr-generate");
    button.disabled = true;
    button.textContent = "Generando…";
    try {
      const data = await api("/pagos/qr/", {
        method: "POST",
        body: {
          conductor_id: nearest.conductor_id,
          linea_id: state.selectedLinea.id,
          monto: monto.toFixed(2),
        },
      });
      state.qrActual = data;
      renderQr(data);
      startQrPolling(data.codigo_qr_uuid);
      toast("QR generado");
    } catch (error) {
      setError("qr-error", errorMessage(error));
    } finally {
      button.disabled = false;
      button.textContent = "Generar QR";
    }
  }

  function renderQr(data) {
    $("qr-form").hidden = true;
    $("qr-result").hidden = false;
    const container = $("qr-canvas");
    container.innerHTML = "";
    if (window.QRCode) {
      new QRCode(container, {
        text: data.codigo_qr_uuid,
        width: 212,
        height: 212,
        colorDark: "#0B0B0B",
        colorLight: "#FFFFFF",
        correctLevel: QRCode.CorrectLevel.M,
      });
    } else {
      container.textContent = "QR no disponible sin conexión.";
    }
    setText("qr-code", `UUID: ${data.codigo_qr_uuid}`);
    setText("qr-status", "Pendiente de confirmación del conductor.");
  }

  function startQrPolling(uuid) {
    stopQrPolling();
    let attempts = 0;
    state.qrPolling = setInterval(async () => {
      attempts += 1;
      if (attempts > 100) {
        stopQrPolling();
        setText("qr-status", "El QR sigue pendiente. Puedes cerrar esta ventana.");
        return;
      }
      try {
        const data = await api(
          `/transacciones/?search=${encodeURIComponent(uuid)}&page_size=5`
        );
        const tx = (data.results || []).find((item) => item.codigo_qr_uuid === uuid);
        if (!tx) return;
        if (tx.estado === "PAGADO") {
          setText("qr-status", "Pago confirmado por el conductor.");
          toast("Pago confirmado");
          stopQrPolling();
        } else if (tx.estado === "ANULADO" || tx.estado === "EXPIRADO") {
          setText("qr-status", `Pago ${tx.estado.toLowerCase()}.`);
          stopQrPolling();
        }
      } catch {
        /* reintento silencioso */
      }
    }, 3000);
  }

  function stopQrPolling() {
    if (state.qrPolling) {
      clearInterval(state.qrPolling);
      state.qrPolling = null;
    }
  }

  // ------------------------------------------------------------- Conductor
  async function loadConductorProfile() {
    try {
      const data = await api("/conductor/perfil/");
      state.conductor = data;
      state.shiftActive = Boolean(data.en_turno);
      state.cupos = data.en_turno
        ? Number(data.cupos_disponibles || 0)
        : Number(data.capacidad_pasajeros || 4);
      renderConductor();
      if (state.shiftActive) {
        ensureGpsSim();
        if (!state.gpsTimer) startGps();
      } else {
        stopGps();
      }
      setViewTimers("conductor");
    } catch (error) {
      setText("drive-status", errorMessage(error));
      toast(errorMessage(error));
    }
  }

  function renderConductor() {
    const conductor = state.conductor;
    if (!conductor) return;
    setText("drive-patente", conductor.patente || "—");
    setText(
      "drive-linea",
      `${conductor.linea_folio || "—"} · ${conductor.linea_nombre || "Sin línea"}`
    );
    setText("drive-cupos", state.cupos);
    setText("cupos-value", state.cupos);
    const chip = $("conductor-status-chip");
    if (chip) {
      chip.textContent = state.shiftActive ? "En turno" : "Fuera de turno";
      chip.classList.toggle("is-yellow", state.shiftActive);
    }
    const shift = $("shift-btn");
    if (shift) shift.textContent = state.shiftActive ? "Finalizar turno" : "Iniciar turno";
    const gps = $("gps-btn");
    if (gps) {
      gps.disabled = !state.shiftActive;
      gps.textContent = state.gpsTimer ? "GPS activo" : "GPS apagado";
      gps.classList.toggle("is-active", Boolean(state.gpsTimer));
    }
    setText(
      "drive-status",
      state.shiftActive
        ? `Turno activo · ${conductor.patente} · ${state.cupos} cupos disponibles.`
        : "Solicita tu código OTP para comenzar."
    );
    const available = $("seat-available");
    const full = $("seat-full");
    if (available) available.classList.toggle("is-active", state.cupos > 0);
    if (full) full.classList.toggle("is-active", state.cupos === 0);
  }

  async function handleShift() {
    if (state.shiftActive) {
      openOtp("finalizar");
    } else {
      openOtp("iniciar");
    }
  }

  async function openOtp(action) {
    const endpoint =
      action === "iniciar"
        ? "/conductor/iniciar-turno/"
        : "/conductor/finalizar-turno/";
    try {
      const data = await api(endpoint, {
        method: "POST",
        body: { solicitar_codigo: true },
      });
      if (data.estado !== "otp_requerido") {
        toast(data.detail || "Operación procesada.");
        return;
      }
      state.otp = { action, codigo: data.codigo_otp };
      setText("otp-title", action === "iniciar" ? "Iniciar turno" : "Finalizar turno");
      setText(
        "otp-hint",
        action === "iniciar"
          ? "Ingresa el código de 6 dígitos para activar tu turno."
          : "Ingresa el código de 6 dígitos para cerrar tu turno."
      );
      const demo = $("otp-demo");
      if (demo) {
        demo.hidden = false;
        demo.textContent = `Código demo: ${data.codigo_otp} · expira en ${data.expires_in_minutes} min`;
      }
      const input = $("otp-input");
      if (input) input.value = "";
      setError("otp-error", "");
      openModal("otp-modal");
      setTimeout(() => input?.focus(), 80);
    } catch (error) {
      toast(errorMessage(error));
    }
  }

  async function handleOtpSubmit(event) {
    event.preventDefault();
    setError("otp-error", "");
    const code = $("otp-input").value.trim();
    if (!/^\d{6}$/.test(code)) {
      setError("otp-error", "El código debe tener 6 dígitos.");
      return;
    }
    const action = state.otp.action;
    const endpoint =
      action === "iniciar"
        ? "/conductor/iniciar-turno/"
        : "/conductor/finalizar-turno/";
    const button = $("otp-form")?.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = "Validando…";
    }
    try {
      await api(endpoint, { method: "POST", body: { codigo_otp: code } });
      closeModal("otp-modal");
      if (action === "iniciar") {
        state.shiftActive = true;
        state.pendingInitialized = false;
        state.seenPagos.clear();
        const desired = Number(state.conductor?.capacidad_pasajeros || 4);
        await api("/conductor/cupos/", {
          method: "POST",
          body: { cupos_disponibles: desired },
        }).catch(() => {});
        await loadConductorProfile();
        ensureGpsSim();
        startGps();
        setViewTimers("conductor");
        toast("Turno iniciado");
      } else {
        state.shiftActive = false;
        stopGps();
        state.cupos = 0;
        await loadConductorProfile();
        setViewTimers("conductor");
        toast("Turno finalizado");
      }
    } catch (error) {
      setError("otp-error", errorMessage(error));
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Confirmar";
      }
    }
  }

  function ensureGpsSim() {
    if (state.gpsSim) return;
    const base = state.paraderos[0] || state.conductor;
    const lat = Number(base?.latitud ?? base?.lat ?? -33.4489);
    const lng = Number(base?.longitud ?? base?.lng ?? -70.6693);
    state.gpsSim = {
      lat: Number.isFinite(lat) ? lat : -33.4489,
      lng: Number.isFinite(lng) ? lng : -70.6693,
      rumbo: 45,
      tick: 0,
    };
  }

  function startGps() {
    if (state.gpsTimer || !state.shiftActive) return;
    ensureGpsSim();
    state.gpsTimer = setInterval(sendTelemetry, 4000);
    renderConductor();
    sendTelemetry();
  }

  function stopGps() {
    if (state.gpsTimer) {
      clearInterval(state.gpsTimer);
      state.gpsTimer = null;
    }
    const gps = $("gps-btn");
    if (gps) {
      gps.textContent = "GPS apagado";
      gps.classList.remove("is-active");
    }
  }

  function toggleGps() {
    if (!state.shiftActive) {
      toast("Inicia turno para activar el GPS.");
      return;
    }
    if (state.gpsTimer) {
      stopGps();
      toast("GPS pausado");
    } else {
      startGps();
      toast("GPS activo");
    }
  }

  async function sendTelemetry() {
    if (!state.shiftActive || !state.conductor || state.gpsSending) return;
    ensureGpsSim();
    state.gpsSending = true;
    const sim = state.gpsSim;
    sim.tick += 1;
    const angle = (sim.tick * 11) % 360;
    const radians = (angle * Math.PI) / 180;
    sim.lat += Math.cos(radians) * 0.00012;
    sim.lng += Math.sin(radians) * 0.0001;
    sim.rumbo = angle;
    const speed = 24 + (sim.tick % 4) * 3;

    try {
      const data = await api("/telemetria/enviar/", {
        method: "POST",
        body: {
          latitud: sim.lat,
          longitud: sim.lng,
          velocidad_kmh: speed,
          rumbo: angle,
          cupos_disponibles: state.cupos,
          timestamp: new Date().toISOString(),
        },
      });
      setText(
        "gps-readout",
        `${sim.lat.toFixed(5)}, ${sim.lng.toFixed(5)} · ${Math.round(
          Number(data.velocidad_calculada_kmh || speed)
        )} km/h · ${state.cupos} cupos`
      );
      setText("gps-last", `Último envío ${new Date().toLocaleTimeString("es-CL")}`);
    } catch (error) {
      if (error.status === 422) {
        toast("Telemetría rechazada por anti-spoofing. Ajustando posición.");
        sim.lat -= Math.cos(radians) * 0.00012;
        sim.lng -= Math.sin(radians) * 0.0001;
      } else {
        toast(errorMessage(error));
      }
    } finally {
      state.gpsSending = false;
    }
  }

  async function setCupos(value) {
    const capacity = Number(state.conductor?.capacidad_pasajeros || 30);
    const next = Math.max(0, Math.min(capacity, Number(value) || 0));
    state.cupos = next;
    renderConductor();
    if (!state.shiftActive) {
      toast("Cupos guardados localmente. Inicia turno para publicarlos.");
      return;
    }
    try {
      await api("/conductor/cupos/", {
        method: "POST",
        body: { cupos_disponibles: next },
      });
      toast(next === 0 ? "Vehículo marcado como lleno" : `${next} cupos disponibles`);
    } catch (error) {
      toast(errorMessage(error));
    }
  }

  async function pollPendingPagos() {
    if (!state.shiftActive || !state.conductor) return;
    try {
      const data = await api(
        `/transacciones/?estado=PENDIENTE&conductor=${state.conductor.id}&page_size=20`
      );
      const list = (data.results || []).filter(
        (pago) =>
          Number(pago.conductor) === Number(state.conductor.id) ||
          pago.conductor_folio === state.conductor.folio_conatacoch
      );
      state.pendingPagos = list;
      renderPendingPagos();
      if (!state.pendingInitialized) {
        list.forEach((pago) => state.seenPagos.add(pago.codigo_qr_uuid));
        state.pendingInitialized = true;
        return;
      }
      const nuevo = list.find((pago) => !state.seenPagos.has(pago.codigo_qr_uuid));
      if (nuevo) {
        state.seenPagos.add(nuevo.codigo_qr_uuid);
        showPaymentAlert(nuevo);
        beep();
        if (navigator.vibrate) navigator.vibrate(180);
      }
    } catch {
      /* polling silencioso */
    }
  }

  function renderPendingPagos() {
    setText("pending-count", String(state.pendingPagos.length));
    const container = $("pending-list");
    if (!container) return;
    if (!state.pendingPagos.length) {
      container.innerHTML = '<p class="empty">Sin pagos pendientes.</p>';
      return;
    }
    container.innerHTML = state.pendingPagos
      .map(
        (pago) => `<article class="pending-item">
          <span>
            <strong>${clp.format(Number(pago.monto || 0))}</strong>
            <small>${esc(pago.pasajero_rut)} · ${esc(
              String(pago.codigo_qr_uuid).slice(0, 8)
            )}…</small>
          </span>
          <button class="btn btn-small btn-primary" type="button" data-confirm-pago="${esc(
            pago.codigo_qr_uuid
          )}">Confirmar</button>
        </article>`
      )
      .join("");
    $$("[data-confirm-pago]", container).forEach((button) => {
      button.addEventListener("click", () => confirmPago(button.dataset.confirmPago));
    });
  }

  function showPaymentAlert(pago) {
    state.paymentAlertPago = pago;
    const alert = $("payment-alert");
    if (!alert) return;
    setText(
      "payment-alert-detail",
      `${clp.format(Number(pago.monto || 0))} · ${pago.pasajero_rut} · ${String(
        pago.codigo_qr_uuid
      ).slice(0, 8)}…`
    );
    alert.hidden = false;
  }

  async function confirmPago(uuid) {
    if (!uuid) return;
    try {
      await api("/pagos/confirmar/", {
        method: "POST",
        body: { codigo_qr_uuid: uuid },
      });
      state.pendingPagos = state.pendingPagos.filter(
        (pago) => pago.codigo_qr_uuid !== uuid
      );
      state.seenPagos.add(uuid);
      renderPendingPagos();
      const alert = $("payment-alert");
      if (alert && state.paymentAlertPago?.codigo_qr_uuid === uuid) {
        alert.hidden = true;
        state.paymentAlertPago = null;
      }
      toast("Pago confirmado");
    } catch (error) {
      toast(errorMessage(error));
    }
  }

  function beep() {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      const context = new AudioContextClass();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "square";
      oscillator.frequency.value = 880;
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.16, context.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.22);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.24);
      oscillator.onended = () => context.close();
    } catch {
      /* audio no disponible */
    }
  }

  // ------------------------------------------------------------------ Admin
  async function loadAdminStats() {
    try {
      const data = await api("/stats/");
      const cards = $$("#admin-stats .stat-card");
      if (cards.length >= 4) {
        cards[0].querySelector("strong").textContent = fmt.format(data.lineas || 0);
        cards[0].querySelector("small").textContent = `${fmt.format(data.folios || 0)} folios`;
        cards[1].querySelector("strong").textContent = fmt.format(data.conductores || 0);
        cards[1].querySelector("small").textContent = `${fmt.format(
          data.vehiculos || 0
        )} vehículos`;
        cards[2].querySelector("strong").textContent = fmt.format(
          data.conductores_en_turno || 0
        );
        cards[2].querySelector("small").textContent = "flota activa";
        cards[3].querySelector("strong").textContent = fmt.format(
          data.transacciones || 0
        );
        cards[3].querySelector("small").textContent = clp.format(
          Number(data.tarifa_promedio || 0)
        );
      }
    } catch {
      /* panel tolerante a fallos */
    }
  }

  function loadAdminSubview(name) {
    state.admin.subview = name;
    $$(".subtab").forEach((tab) => {
      const active = tab.dataset.admin === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    $$(".admin-panel").forEach((panel) => {
      panel.hidden = panel.id !== `admin-${name}`;
    });
    if (name === "conductores") loadConductores(state.admin.conductoresPage);
    if (name === "lineas") loadLineas(state.admin.lineasPage);
    if (name === "flota") {
      initAdminMap();
      loadAdminFlota();
      setTimeout(() => state.adminMap?.invalidateSize(), 90);
    }
    if (name === "pagos") loadPagos(state.admin.pagosPage, state.admin.pagosEstado);
    setViewTimers("admin");
  }

  async function loadConductores(page = 1, search = state.admin.conductoresSearch) {
    state.admin.conductoresPage = page;
    state.admin.conductoresSearch = search;
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (search) params.set("search", search);
    try {
      const data = await api(`/conductores/?${params.toString()}`);
      state.admin.conductores = data.results || [];
      state.admin.conductoresTotal = data.count || 0;
      renderConductores();
      renderPager("conductores-page", page, data.count || 0);
    } catch (error) {
      const list = $("admin-conductores-list");
      if (list) list.innerHTML = `<p class="empty">${esc(errorMessage(error))}</p>`;
    }
  }

  function renderConductores() {
    const list = $("admin-conductores-list");
    if (!list) return;
    if (!state.admin.conductores.length) {
      list.innerHTML = '<p class="empty">Sin conductores para el filtro.</p>';
      return;
    }
    list.innerHTML = state.admin.conductores
      .map(
        (conductor) => `<article class="data-item">
          <div class="data-item-top">
            <span>
              <strong>${esc(conductor.usuario_nombre || "Conductor")}</strong>
              <small>${esc(conductor.usuario_rut || "—")} · ${esc(
                conductor.folio_conatacoch
              )}</small>
            </span>
            <span class="badge ${conductor.en_turno ? "is-yellow" : ""}">${
              conductor.en_turno ? "En turno" : "Fuera"
            }</span>
          </div>
          <div class="row-meta">
            <span>${esc(conductor.patente || "—")}</span>
            <span>Línea ${esc(conductor.linea_folio ?? "—")}</span>
            <span>${esc(conductor.cupos_disponibles ?? 0)} cupos</span>
            <span>ID ${esc(conductor.id)}</span>
          </div>
          <div class="data-actions">
            <button class="btn btn-small btn-ghost" type="button" data-action="edit-conductor" data-id="${esc(
              conductor.id
            )}">Editar</button>
            <button class="btn btn-small btn-ghost" type="button" data-action="delete-conductor" data-id="${esc(
              conductor.id
            )}">Eliminar</button>
          </div>
        </article>`
      )
      .join("");
  }

  async function loadLineaOptions() {
    if (state.admin.lineaOptions) return state.admin.lineaOptions;
    const lineas = await fetchAll("/lineas/?page_size=100");
    state.admin.lineaOptions = lineas;
    const select = $("conductor-linea");
    if (select) {
      select.innerHTML =
        '<option value="">Selecciona una línea</option>' +
        lineas
          .map(
            (linea) =>
              `<option value="${esc(linea.id)}">#${esc(linea.folio)} · ${esc(
                linea.nombre_recorrido
              )} · ${esc(linea.comuna_origen)}→${esc(linea.comuna_destino)}</option>`
          )
          .join("");
    }
    return lineas;
  }

  async function openConductorForm(editId) {
    await loadLineaOptions();
    const form = $("conductor-form");
    if (!form) return;
    state.admin.conductorEditId = editId || null;
    form.hidden = false;
    setError("conductor-error", "");
    const fields = {
      rut: $("conductor-rut"),
      nombre: $("conductor-nombre"),
      email: $("conductor-email"),
      password: $("conductor-password"),
    };
    if (editId) {
      const conductor = state.admin.conductores.find((item) => Number(item.id) === Number(editId));
      if (!conductor) {
        toast("Conductor no encontrado en la página actual.");
        form.hidden = true;
        return;
      }
      $("conductor-edit-id").value = conductor.id;
      fields.rut.value = conductor.usuario_rut || "";
      fields.nombre.value = conductor.usuario_nombre || "";
      fields.email.value = "";
      fields.password.value = "";
      Object.values(fields).forEach((field) => {
        field.disabled = true;
        field.required = false;
      });
      $("conductor-folio").value = conductor.folio_conatacoch || "";
      $("conductor-patente").value = conductor.patente || "";
      $("conductor-cupos").value = conductor.cupos_disponibles ?? 0;
      $("conductor-marca").value = "";
      $("conductor-capacidad").value = 4;
      $("conductor-submit").textContent = "Guardar cambios";

      let lineaId = conductor.linea_id;
      if (!lineaId && conductor.vehiculo) {
        try {
          const vehiculo = await api(`/vehiculos/${conductor.vehiculo}/`);
          lineaId = vehiculo.linea;
        } catch {
          /* sin linea */
        }
      }
      if (lineaId) $("conductor-linea").value = String(lineaId);
    } else {
      $("conductor-edit-id").value = "";
      fields.rut.value = "";
      fields.nombre.value = "";
      fields.email.value = "";
      fields.password.value = "";
      Object.values(fields).forEach((field) => {
        field.disabled = false;
        field.required = true;
      });
      $("conductor-folio").value = "";
      $("conductor-patente").value = "";
      $("conductor-cupos").value = 4;
      $("conductor-marca").value = "";
      $("conductor-capacidad").value = 4;
      $("conductor-linea").value = "";
      $("conductor-submit").textContent = "Guardar conductor";
    }
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function validarRut(rut) {
    const clean = String(rut || "").replace(/[.\-\s]/g, "").toUpperCase();
    if (!/^\d{7,8}[0-9K]$/.test(clean)) return false;
    const body = clean.slice(0, -1);
    const dv = clean.slice(-1);
    let sum = 0;
    let multiplier = 2;
    for (let i = body.length - 1; i >= 0; i -= 1) {
      sum += Number(body[i]) * multiplier;
      multiplier = multiplier === 7 ? 2 : multiplier + 1;
    }
    const remainder = 11 - (sum % 11);
    const expected = remainder === 11 ? "0" : remainder === 10 ? "K" : String(remainder);
    return dv === expected;
  }

  async function handleConductorSubmit(event) {
    event.preventDefault();
    setError("conductor-error", "");
    const editId = $("conductor-edit-id").value;
    const patente = $("conductor-patente").value.trim().toUpperCase();
    const folio = $("conductor-folio").value.trim();
    const lineaId = Number($("conductor-linea").value);
    if (!/^[A-Z]{2,4}-?[0-9]{2,4}$/.test(patente)) {
      setError("conductor-error", "Patente inválida. Ejemplo: ABCD-12.");
      return;
    }
    if (!folio) {
      setError("conductor-error", "El folio CONATACOCH es obligatorio.");
      return;
    }
    if (!lineaId) {
      setError("conductor-error", "Selecciona una línea.");
      return;
    }

    const button = $("conductor-submit");
    button.disabled = true;
    button.textContent = "Guardando…";
    try {
      if (editId) {
        await api(`/admin-api/conductores/${editId}/`, {
          method: "PATCH",
          body: {
            folio_conatacoch: folio,
            patente,
            linea_id: lineaId,
            cupos_disponibles: Number($("conductor-cupos").value || 0),
            marca_modelo: $("conductor-marca").value.trim() || "Por definir",
            capacidad_pasajeros: Number($("conductor-capacidad").value || 4),
          },
        });
        toast("Conductor actualizado");
      } else {
        const rut = $("conductor-rut").value.trim();
        const email = $("conductor-email").value.trim();
        const password = $("conductor-password").value;
        if (!validarRut(rut)) {
          setError("conductor-error", "RUT inválido. Revisa el dígito verificador.");
          return;
        }
        if (!email) {
          setError("conductor-error", "El email es obligatorio.");
          return;
        }
        if (password.length < 12) {
          setError("conductor-error", "La contraseña debe tener al menos 12 caracteres.");
          return;
        }
        await api("/admin-api/conductores/completo/", {
          method: "POST",
          body: {
            rut,
            nombre: $("conductor-nombre").value.trim(),
            email,
            password,
            folio_conatacoch: folio,
            patente,
            linea_id: lineaId,
            cupos_disponibles: Number($("conductor-cupos").value || 0),
            marca_modelo: $("conductor-marca").value.trim() || "Por definir",
            capacidad_pasajeros: Number($("conductor-capacidad").value || 4),
          },
        });
        toast("Conductor creado");
      }
      $("conductor-form").hidden = true;
      state.admin.conductorEditId = null;
      await loadConductores(editId ? state.admin.conductoresPage : 1);
      await loadAdminStats();
    } catch (error) {
      setError("conductor-error", errorMessage(error));
    } finally {
      button.disabled = false;
      button.textContent = editId ? "Guardar cambios" : "Guardar conductor";
    }
  }

  async function deleteConductor(id) {
    if (!window.confirm("¿Eliminar este conductor? Esta acción no se puede deshacer.")) {
      return;
    }
    try {
      await api(`/admin-api/conductores/${id}/`, { method: "DELETE" });
      toast("Conductor eliminado");
      await loadConductores(state.admin.conductoresPage);
      await loadAdminStats();
    } catch (error) {
      toast(errorMessage(error));
    }
  }

  async function loadLineas(page = 1, search = state.admin.lineasSearch) {
    state.admin.lineasPage = page;
    state.admin.lineasSearch = search;
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (search) params.set("search", search);
    try {
      const data = await api(`/lineas/?${params.toString()}`);
      state.admin.lineas = data.results || [];
      state.admin.lineasTotal = data.count || 0;
      renderLineas();
      renderPager("lineas-page", page, data.count || 0);
    } catch (error) {
      const list = $("admin-lineas-list");
      if (list) list.innerHTML = `<p class="empty">${esc(errorMessage(error))}</p>`;
    }
  }

  function renderLineas() {
    const list = $("admin-lineas-list");
    if (!list) return;
    if (!state.admin.lineas.length) {
      list.innerHTML = '<p class="empty">Sin líneas para el filtro.</p>';
      return;
    }
    list.innerHTML = state.admin.lineas
      .map(
        (linea) => `<article class="data-item">
          <div class="data-item-top">
            <span>
              <strong>#${esc(linea.folio)} · ${esc(linea.nombre_recorrido)}</strong>
              <small>${esc(linea.comuna_origen)} → ${esc(linea.comuna_destino)}</small>
            </span>
            <span class="badge">${esc(linea.tipo_trazado || "PRINCIPAL")}</span>
          </div>
          <div class="row-meta">
            <span>${esc(linea.tipo_servicio)}</span>
            <span>${esc(linea.domicilio_origen)}</span>
            <span>${esc(linea.domicilio_destino)}</span>
          </div>
          <div class="tarifa-row">
            <input id="tarifa-${esc(linea.id)}" type="number" min="0" step="50" value="${esc(
              Number(linea.tarifa_actual || 0)
            )}" aria-label="Tarifa de la línea ${esc(linea.folio)}">
            <button class="btn btn-small btn-primary" type="button" data-action="save-tarifa" data-id="${esc(
              linea.id
            )}">Guardar tarifa</button>
            <button class="btn btn-small btn-ghost" type="button" data-action="edit-linea" data-id="${esc(
              linea.id
            )}">Editar</button>
          </div>
        </article>`
      )
      .join("");
  }

  async function saveTarifa(id) {
    const input = $(`tarifa-${id}`);
    if (!input) return;
    const value = Number(input.value);
    if (!Number.isFinite(value) || value < 0) {
      toast("Tarifa inválida.");
      return;
    }
    try {
      await api("/admin-api/tarifas/", {
        method: "POST",
        body: { linea_id: id, tarifa_actual: value.toFixed(2) },
      });
      toast("Tarifa actualizada");
      await loadLineas(state.admin.lineasPage);
    } catch (error) {
      toast(errorMessage(error));
    }
  }

  function openLineaForm(editId) {
    const form = $("linea-form");
    if (!form) return;
    state.admin.lineaEditId = editId || null;
    form.hidden = false;
    setError("linea-error", "");
    const naturalFields = [
      $("linea-folio"),
      $("linea-nombre"),
      $("linea-trazado"),
    ];
    if (editId) {
      const linea = state.admin.lineas.find((item) => Number(item.id) === Number(editId));
      if (!linea) {
        toast("Línea no encontrada en la página actual.");
        form.hidden = true;
        return;
      }
      $("linea-edit-id").value = linea.id;
      $("linea-region").value = linea.region;
      $("linea-folio").value = linea.folio;
      $("linea-tipo-servicio").value = linea.tipo_servicio;
      $("linea-nombre").value = linea.nombre_recorrido;
      $("linea-trazado").value = linea.tipo_trazado;
      $("linea-origen").value = linea.nombre_origen;
      $("linea-comuna-origen").value = linea.comuna_origen;
      $("linea-domicilio-origen").value = linea.domicilio_origen;
      $("linea-destino").value = linea.nombre_destino;
      $("linea-comuna-destino").value = linea.comuna_destino;
      $("linea-domicilio-destino").value = linea.domicilio_destino;
      $("linea-tarifa").value = Number(linea.tarifa_actual || 0);
      naturalFields.forEach((field) => {
        if (field) field.disabled = true;
      });
      $("linea-submit").textContent = "Guardar cambios";
    } else {
      $("linea-edit-id").value = "";
      $("linea-region").value = 13;
      $("linea-folio").value = "";
      $("linea-tipo-servicio").value = "AUTOMOVIL URBANO TAXI COLECTIVO";
      $("linea-nombre").value = "";
      $("linea-trazado").value = "PRINCIPAL";
      $("linea-origen").value = "";
      $("linea-comuna-origen").value = "";
      $("linea-domicilio-origen").value = "";
      $("linea-destino").value = "";
      $("linea-comuna-destino").value = "";
      $("linea-domicilio-destino").value = "";
      $("linea-tarifa").value = 1000;
      naturalFields.forEach((field) => {
        if (field) field.disabled = false;
      });
      $("linea-submit").textContent = "Guardar línea";
    }
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function handleLineaSubmit(event) {
    event.preventDefault();
    setError("linea-error", "");
    const payload = {
      region: Number($("linea-region").value),
      folio: Number($("linea-folio").value),
      tipo_servicio: $("linea-tipo-servicio").value,
      nombre_recorrido: $("linea-nombre").value.trim(),
      tipo_trazado: $("linea-trazado").value,
      nombre_origen: $("linea-origen").value.trim(),
      comuna_origen: $("linea-comuna-origen").value.trim(),
      domicilio_origen: $("linea-domicilio-origen").value.trim(),
      nombre_destino: $("linea-destino").value.trim(),
      comuna_destino: $("linea-comuna-destino").value.trim(),
      domicilio_destino: $("linea-domicilio-destino").value.trim(),
      tarifa_actual: Number($("linea-tarifa").value || 0).toFixed(2),
    };
    if (
      !payload.folio ||
      !payload.nombre_recorrido ||
      !payload.comuna_origen ||
      !payload.comuna_destino
    ) {
      setError("linea-error", "Completa folio, recorrido y comunas.");
      return;
    }
    const button = $("linea-submit");
    button.disabled = true;
    button.textContent = "Guardando…";
    try {
      const editando = Boolean(state.admin.lineaEditId);
      const paginaDestino = editando ? state.admin.lineasPage : 1;
      await api("/admin-api/lineas/upsert/", { method: "POST", body: payload });
      toast(editando ? "Línea actualizada" : "Línea creada");
      $("linea-form").hidden = true;
      state.admin.lineaEditId = null;
      state.admin.lineaOptions = null;
      await loadLineas(paginaDestino);
      await loadAdminStats();
    } catch (error) {
      setError("linea-error", errorMessage(error));
    } finally {
      button.disabled = false;
      button.textContent = "Guardar línea";
    }
  }

  async function loadAdminFlota() {
    try {
      const data = await api("/telemetria/flota/");
      state.adminFleet = data.vehiculos || [];
      setText(
        "admin-fleet-updated",
        `Actualizado ${new Date().toLocaleTimeString("es-CL")}`
      );
      renderAdminFleet();
      initAdminMap();
      updateAdminMap(!state.adminMapFitted);
    } catch (error) {
      const list = $("admin-fleet-list");
      if (list) list.innerHTML = `<p class="empty">${esc(errorMessage(error))}</p>`;
    }
  }

  function renderAdminFleet() {
    const list = $("admin-fleet-list");
    if (!list) return;
    if (!state.adminFleet.length) {
      list.innerHTML = '<p class="empty">Sin telemetría de flota en este momento.</p>';
      return;
    }
    list.innerHTML = state.adminFleet
      .map(
        (vehiculo) => `<article class="data-item">
          <div class="data-item-top">
            <span>
              <strong>${esc(vehiculo.patente)} · ${esc(vehiculo.folio_conatacoch)}</strong>
              <small>${esc(vehiculo.linea_nombre)} · ${relativeAge(
                vehiculo.edad_segundos
              )}</small>
            </span>
            <span class="badge is-yellow">${esc(vehiculo.cupos_disponibles)} cupos</span>
          </div>
          <div class="row-meta">
            <span>${Math.round(Number(vehiculo.velocidad_kmh || 0))} km/h</span>
            <span>${Number(vehiculo.latitud).toFixed(4)}, ${Number(
              vehiculo.longitud
            ).toFixed(4)}</span>
            <span>${esc(vehiculo.usuario_nombre)}</span>
          </div>
        </article>`
      )
      .join("");
  }

  async function loadPagos(page = 1, estado = state.admin.pagosEstado, silent = false) {
    state.admin.pagosPage = page;
    state.admin.pagosEstado = estado;
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (estado) params.set("estado", estado);
    try {
      const data = await api(`/transacciones/?${params.toString()}`);
      state.admin.pagos = data.results || [];
      state.admin.pagosTotal = data.count || 0;
      renderPagos();
      renderPager("pagos-page", page, data.count || 0);
    } catch (error) {
      if (!silent) {
        const list = $("admin-pagos-list");
        if (list) list.innerHTML = `<p class="empty">${esc(errorMessage(error))}</p>`;
      }
    }
  }

  function renderPagos() {
    const list = $("admin-pagos-list");
    if (!list) return;
    if (!state.admin.pagos.length) {
      list.innerHTML = '<p class="empty">Sin transacciones para el filtro.</p>';
      return;
    }
    list.innerHTML = state.admin.pagos
      .map(
        (pago) => `<article class="data-item">
          <div class="data-item-top">
            <span>
              <strong>${clp.format(Number(pago.monto || 0))}</strong>
              <small>${esc(pago.pasajero_rut)} · ${esc(pago.conductor_folio)}</small>
            </span>
            <span class="badge ${pago.estado === "PAGADO" ? "is-yellow" : ""}">${esc(
              pago.estado_display || pago.estado
            )}</span>
          </div>
          <div class="row-meta">
            <span>Línea ${esc(pago.linea_folio)}</span>
            <span>${formatDate(pago.fecha_hora)}</span>
            <span>${esc(String(pago.codigo_qr_uuid).slice(0, 13))}…</span>
          </div>
        </article>`
      )
      .join("");
  }

  // ----------------------------------------------------------------- Cuenta
  function renderAccount() {
    const usuario = state.session?.usuario;
    if (!usuario) return;
    const initials = String(usuario.nombre || "?")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("");
    setText("account-avatar", initials || "?");
    setText("account-name", usuario.nombre || "—");
    setText("account-email", usuario.email || "—");
    setText("account-rut", usuario.rut || "—");
    setText("account-role", ROLE_LABEL[usuario.rol] || usuario.rol || "—");
    setText("account-session", "JWT activo");
  }

  // ----------------------------------------------------------------- Modales
  function openModal(id) {
    const modal = $(id);
    if (!modal) return;
    modal.hidden = false;
    document.body.classList.add("is-scroll-lock");
  }

  function closeModal(id) {
    const modal = $(id);
    if (!modal) return;
    modal.hidden = true;
    if (id === "qr-modal") stopQrPolling();
    if (id === "otp-modal") state.otp = { action: null, codigo: null };
    if (!$$(".modal:not([hidden])").length) {
      document.body.classList.remove("is-scroll-lock");
    }
  }

  function closeAllModals() {
    $$(".modal").forEach((modal) => {
      modal.hidden = true;
    });
    document.body.classList.remove("is-scroll-lock");
    stopQrPolling();
    state.otp = { action: null, codigo: null };
  }

  function bindModals() {
    $$("[data-close]").forEach((element) => {
      element.addEventListener("click", () => closeModal(element.dataset.close));
    });
  }

  // ------------------------------------------------------------------- Init
  function init() {
    bindLogin();
    bindAppEvents();
    bindModals();
    checkApi();

    const saved = loadStoredSession();
    if (saved?.access && saved?.usuario) {
      state.session = saved;
      enterApp();
    } else {
      showLogin();
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
