/**
 * CONATACOCH · App móvil (Fase 2)
 * Consume endpoints públicos y agregados del backend.
 * Negro / blanco / amarillo · minimalista · mobile-first.
 */
(() => {
  "use strict";

  const API = "/api";
  const VIEWS = ["inicio", "rutas", "flota", "mas"];
  const state = { page: 1, search: "", total: 0, pageSize: 10, rutasCargadas: false };

  const $ = (id) => document.getElementById(id);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  const fmt = new Intl.NumberFormat("es-CL");
  const clp = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  });

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[ch]));

  async function fetchJSON(path, timeoutMs = 9000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(API + path, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally {
      clearTimeout(timer);
    }
  }

  // ------------------------------------------------------------------ Toast
  let toastTimer;
  function toast(message) {
    const el = $("toast");
    if (!el) return;
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
  }

  // ---------------------------------------------------------------- Status
  function setStatus(id, stateName, text) {
    const el = $(id);
    if (!el) return;
    el.dataset.state = stateName;
    const label = el.querySelector("span:last-child");
    if (label) label.textContent = text;
  }

  function setStatusGroup(ids, stateName, text) {
    ids.forEach((id) => setStatus(id, stateName, text));
  }

  function setText(id, value) {
    const el = $(id);
    if (el) el.textContent = value;
  }

  function marcarServicio(nombre, clase) {
    $$(`[data-service-dot="${nombre}"]`).forEach((dot) => {
      const row = dot.closest(".service-row");
      if (!row) return;
      row.classList.remove("is-ok", "is-warn", "is-err");
      if (clase) row.classList.add(clase);
    });
  }

  // ------------------------------------------------------------ Navegación
  function showView(name, actualizarHash = true) {
    if (!VIEWS.includes(name)) name = "inicio";

    $$(".view").forEach((view) => {
      view.classList.toggle("is-active", view.id === `view-${name}`);
    });
    $$(".tab").forEach((tab) => {
      const activo = tab.dataset.view === name;
      tab.classList.toggle("is-active", activo);
      if (activo) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    });

    const main = $("app-main");
    if (main) main.scrollTop = 0;

    if (actualizarHash && window.location.hash !== `#${name}`) {
      history.replaceState(null, "", `#${name}`);
    }

    if (name === "rutas" && !state.rutasCargadas) {
      loadRoutes();
    }
  }

  function bindNavigation() {
    $$(".tab").forEach((tab) => {
      tab.addEventListener("click", () => showView(tab.dataset.view));
    });
    $$("[data-go]").forEach((btn) => {
      btn.addEventListener("click", () => showView(btn.dataset.go));
    });
    $$("[data-view-link]").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        showView(link.dataset.viewLink);
      });
    });
    window.addEventListener("hashchange", () => {
      showView(window.location.hash.replace("#", ""), false);
    });
  }

  // ----------------------------------------------------------- Salud / stats
  async function loadHealth() {
    const inicio = performance.now();
    try {
      const data = await fetchJSON("/health/");
      const apiMs = performance.now() - inicio;
      const components = data.components || {};
      const mysql = components.mysql || {};
      const mongo = components.mongodb || {};
      const mysqlOk = mysql.status === "ok";
      const mongoOk = mongo.status === "ok";

      setStatusGroup(["api-status", "api-status-2", "api-status-3", "card-api"], "ok", "Operativo");
      setText("api-latency", `latencia ${Math.round(apiMs)} ms`);
      marcarServicio("api", "is-ok");

      setStatusGroup(
        ["card-mysql", "mysql-status-2", "mysql-status"],
        mysqlOk ? "ok" : "error",
        mysqlOk ? "Conectado" : "Sin conexión"
      );
      setText("mysql-latency", `latencia ${mysql.latency_ms ?? "--"} ms`);
      marcarServicio("mysql", mysqlOk ? "is-ok" : "is-err");

      setStatusGroup(
        ["card-mongo", "mongo-status-2", "mongo-status"],
        mongoOk ? "ok" : "degraded",
        mongoOk ? "Conectado" : "Degradado"
      );
      setText(
        "mongo-mode",
        `modo ${mongo.mode || "--"} · ${mongo.latency_ms ?? "--"} ms`
      );
      marcarServicio("mongo", mongoOk ? "is-ok" : "is-warn");

      setText(
        "health-detail",
        `Última verificación: ${new Date().toLocaleTimeString("es-CL")}`
      );
    } catch (error) {
      setStatusGroup(["api-status", "api-status-2", "api-status-3", "card-api"], "error", "Sin respuesta");
      setStatusGroup(["card-mysql", "mysql-status-2", "mysql-status"], "error", "Desconocido");
      setStatusGroup(["card-mongo", "mongo-status-2", "mongo-status"], "error", "Desconocido");
      marcarServicio("api", "is-err");
      marcarServicio("mysql", "is-err");
      marcarServicio("mongo", "is-err");
      setText("health-detail", "No fue posible contactar el backend.");
      console.error("Health error", error);
    }
  }

  async function loadStats() {
    try {
      const data = await fetchJSON("/stats/");
      const lineas = fmt.format(data.lineas ?? 0);
      const paraderos = fmt.format(data.paraderos ?? 0);
      const conductores = fmt.format(data.conductores ?? 0);
      const enTurno = fmt.format(data.conductores_en_turno ?? 0);
      const vehiculos = fmt.format(data.vehiculos ?? 0);
      const pasajeros = fmt.format(data.pasajeros ?? 0);
      const tarifa = clp.format(data.tarifa_promedio || 0);

      setText("hero-lineas", lineas);
      setText("hero-paraderos", paraderos);
      setText("hero-comunas", fmt.format(data.comunas ?? 0));
      setText("hero-turno", enTurno);

      setText("m-lineas", lineas);
      setText("m-folios", `${fmt.format(data.folios ?? 0)} folios`);
      setText("m-paraderos", paraderos);
      setText("m-conductores", conductores);
      setText("m-turno", `${enTurno} en turno`);
      setText("m-vehiculos", vehiculos);
      setText("m-pasajeros", pasajeros);
      setText("m-tarifa", tarifa);

      setText("f-turno", enTurno);
      setText("f-conductores", `${conductores} registrados`);
      setText("f-vehiculos", vehiculos);
      setText("f-pasajeros", pasajeros);
      setText("f-tarifa", tarifa);

      setText("last-update", `Actualizado ${new Date().toLocaleTimeString("es-CL")}`);
    } catch (error) {
      setText("last-update", "No disponible");
      console.error("Stats error", error);
    }
  }

  // -------------------------------------------------------------- Recorridos
  function renderRows(results) {
    const body = $("routes-body");
    if (!body) return;

    if (!results.length) {
      body.innerHTML = '<div class="empty-state">Sin rutas para el filtro aplicado.</div>';
      return;
    }

    body.innerHTML = results.map((ruta) => {
      const alternativo = String(ruta.tipo_trazado).toUpperCase() === "ALTERNATIVO";
      return `<article class="route-card">
        <div class="route-top">
          <span class="folio">#${esc(ruta.folio)}</span>
          <span class="badge ${alternativo ? "alt" : ""}">${esc(ruta.tipo_trazado || "RUTA")}</span>
        </div>
        <h3>${esc(ruta.nombre_recorrido)}</h3>
        <p class="route-path">
          <span>${esc(ruta.comuna_origen || "Origen")}</span>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h15M14 7l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span>${esc(ruta.comuna_destino || "Destino")}</span>
        </p>
        <div class="route-bottom">
          <span class="route-from">${esc(ruta.domicilio_origen || "Recorrido regional")}</span>
          <span class="route-fare">${clp.format(Number(ruta.tarifa_actual || 0))}</span>
        </div>
      </article>`;
    }).join("");
  }

  async function loadRoutes() {
    const body = $("routes-body");
    if (body && !state.rutasCargadas) {
      body.innerHTML = '<div class="route-card skeleton" aria-hidden="true"></div>'.repeat(3);
    }

    const params = new URLSearchParams({
      page: String(state.page),
      page_size: String(state.pageSize),
    });
    if (state.search) params.set("search", state.search);

    try {
      const data = await fetchJSON(`/lineas/?${params.toString()}`);
      const results = data.results || [];
      renderRows(results);
      state.total = data.count || results.length;
      state.rutasCargadas = true;

      const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
      setText("routes-count", `${fmt.format(state.total)} rutas`);
      setText("page-label", `${state.page} / ${pages}`);

      const prev = $("prev-page");
      const next = $("next-page");
      if (prev) prev.disabled = !data.previous;
      if (next) next.disabled = !data.next;
    } catch (error) {
      if (body) {
        body.innerHTML = '<div class="empty-state">No se pudo cargar el catálogo. Revisa el backend y reintenta.</div>';
      }
      setText("routes-count", "Sin conexión");
      console.error("Routes error", error);
    }
  }

  // ----------------------------------------------------------------- Eventos
  function bindEvents() {
    const search = $("route-search");
    let timer;
    if (search) {
      search.addEventListener("input", (event) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          state.search = event.target.value.trim();
          state.page = 1;
          loadRoutes();
        }, 300);
      });
      search.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          clearTimeout(timer);
          state.search = event.target.value.trim();
          state.page = 1;
          loadRoutes();
        }
      });
    }

    $("prev-page")?.addEventListener("click", () => {
      if (state.page > 1) {
        state.page -= 1;
        loadRoutes();
      }
    });
    $("next-page")?.addEventListener("click", () => {
      const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
      if (state.page < pages) {
        state.page += 1;
        loadRoutes();
      }
    });

    $("refresh-btn")?.addEventListener("click", () => {
      refreshAll();
      toast("Datos actualizados");
    });
  }

  function refreshAll() {
    loadHealth();
    loadStats();
    if (state.rutasCargadas) loadRoutes();
  }

  function init() {
    setText("year", new Date().getFullYear());
    bindNavigation();
    bindEvents();

    const inicial = window.location.hash.replace("#", "");
    showView(VIEWS.includes(inicial) ? inicial : "inicio", false);

    refreshAll();
    setInterval(loadHealth, 30000);
    setInterval(loadStats, 60000);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
