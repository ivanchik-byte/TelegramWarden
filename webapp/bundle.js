(() => {
  // ../../../../tmp/webapp_code.jsx
  var { useState, useEffect, useCallback, useRef, useMemo } = window.React;
  var _initDataStr = "";
  function getTelegramWebApp() {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      tg.setHeaderColor?.("#07090e");
      tg.setBackgroundColor?.("#07090e");
      _initDataStr = tg.initData || "";
    }
    return tg;
  }
  async function apiRequest(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": _initDataStr,
      ...options.headers
    };
    const res = await fetch(endpoint, { ...options, headers });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server Error (HTTP ${res.status})`);
    }
    return res.json();
  }
  var Api = {
    getChats: () => apiRequest("/api/chats"),
    getSettings: (chatId) => apiRequest(`/api/chats/${chatId}`),
    saveSettings: (chatId, data) => apiRequest(`/api/chats/${chatId}`, { method: "PATCH", body: JSON.stringify(data) }),
    getStats: (chatId) => apiRequest(`/api/stats/${chatId}`),
    getLogs: (chatId, limit = 50) => apiRequest(`/api/stats/${chatId}/logs?limit=${limit}`),
    scanText: (text) => apiRequest("/api/scan", { method: "POST", body: JSON.stringify({ text }) }),
    getDbTables: () => apiRequest("/api/database/tables"),
    getDbRecords: (table, limit = 25, offset = 0, search = "") => apiRequest(`/api/database/records?table=${table}&limit=${limit}&offset=${offset}${search ? "&search=" + encodeURIComponent(search) : ""}`)
  };
  var Icons = {
    shield: (c = "currentColor", s = 18) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" })),
    chart: (c = "currentColor", s = 18) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("line", { x1: "18", y1: "20", x2: "18", y2: "10" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "20", x2: "12", y2: "4" }), /* @__PURE__ */ React.createElement("line", { x1: "6", y1: "20", x2: "6", y2: "14" })),
    tune: (c = "currentColor", s = 18) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "7", r: "3" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "10", x2: "12", y2: "21" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "1", x2: "12", y2: "4" }), /* @__PURE__ */ React.createElement("circle", { cx: "6", cy: "14", r: "3" }), /* @__PURE__ */ React.createElement("line", { x1: "6", y1: "17", x2: "6", y2: "21" }), /* @__PURE__ */ React.createElement("line", { x1: "6", y1: "1", x2: "6", y2: "11" }), /* @__PURE__ */ React.createElement("circle", { cx: "18", cy: "17", r: "3" }), /* @__PURE__ */ React.createElement("line", { x1: "18", y1: "20", x2: "18", y2: "21" }), /* @__PURE__ */ React.createElement("line", { x1: "18", y1: "1", x2: "18", y2: "14" })),
    list: (c = "currentColor", s = 18) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" }), /* @__PURE__ */ React.createElement("polyline", { points: "14 2 14 8 20 8" }), /* @__PURE__ */ React.createElement("line", { x1: "16", y1: "13", x2: "8", y2: "13" }), /* @__PURE__ */ React.createElement("line", { x1: "16", y1: "17", x2: "8", y2: "17" })),
    search: (c = "currentColor", s = 18) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("circle", { cx: "11", cy: "11", r: "8" }), /* @__PURE__ */ React.createElement("line", { x1: "21", y1: "21", x2: "16.65", y2: "16.65" })),
    database: (c = "currentColor", s = 18) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("ellipse", { cx: "12", cy: "5", rx: "9", ry: "3" }), /* @__PURE__ */ React.createElement("path", { d: "M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" }), /* @__PURE__ */ React.createElement("path", { d: "M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" })),
    refresh: (c = "currentColor", s = 14) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("polyline", { points: "23 4 23 10 17 10" }), /* @__PURE__ */ React.createElement("path", { d: "M20.49 15a9 9 0 11-2.12-9.36L23 10" })),
    check: (c = "currentColor", s = 16) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "2.5", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("polyline", { points: "20 6 9 17 4 12" })),
    alert: (c = "currentColor", s = 16) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("path", { d: "M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "9", x2: "12", y2: "13" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "17", x2: "12.01", y2: "17" })),
    clock: (c = "currentColor", s = 12) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "10" }), /* @__PURE__ */ React.createElement("polyline", { points: "12 6 12 12 16 14" })),
    table: (c = "currentColor", s = 14) => /* @__PURE__ */ React.createElement("svg", { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: c, strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" }, /* @__PURE__ */ React.createElement("rect", { x: "3", y: "3", width: "18", height: "18", rx: "2" }), /* @__PURE__ */ React.createElement("line", { x1: "3", y1: "9", x2: "21", y2: "9" }), /* @__PURE__ */ React.createElement("line", { x1: "3", y1: "15", x2: "21", y2: "15" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "3", x2: "12", y2: "21" }))
  };
  function AnimatedCounter({ value, colorClass = "text-white" }) {
    const [count, setCount] = useState(0);
    useEffect(() => {
      const target = Number(value) || 0;
      if (target === 0) {
        setCount(0);
        return;
      }
      const duration = 500;
      const start = Date.now();
      const frame = () => {
        const progress = Math.min((Date.now() - start) / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        setCount(Math.round(easeOut * target));
        if (progress < 1) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    }, [value]);
    return /* @__PURE__ */ React.createElement("span", { className: `font-mono-code text-2xl font-bold tracking-tight ${colorClass}` }, count);
  }
  function SegmentedControl({ options, value, onChange }) {
    return /* @__PURE__ */ React.createElement("div", { className: "inline-flex bg-[#07090e] p-1 rounded-xl border border-[#1e2738] gap-1" }, options.map((opt) => {
      const active = opt.value === value;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: opt.value,
          onClick: () => {
            onChange(opt.value);
            window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
          },
          className: `px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${active ? "bg-[#e11d48] text-white shadow-md shadow-rose-950/50" : "text-slate-400 hover:text-slate-200"}`
        },
        opt.label
      );
    }));
  }
  function StepperControl({ value, min = 0, max = 100, step = 1, suffix = "", onChange }) {
    return /* @__PURE__ */ React.createElement("div", { className: "flex items-center bg-[#07090e] border border-[#1e2738] rounded-xl overflow-hidden" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          if (value > min) {
            onChange(Math.max(min, value - step));
            window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
          }
        },
        disabled: value <= min,
        className: "w-9 h-8 flex items-center justify-center text-slate-400 active:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none text-base font-bold"
      },
      "-"
    ), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code px-2 text-xs font-bold text-slate-200 min-w-[36px] text-center" }, value, suffix), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          if (value < max) {
            onChange(Math.min(max, value + step));
            window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
          }
        },
        disabled: value >= max,
        className: "w-9 h-8 flex items-center justify-center text-slate-400 active:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none text-base font-bold"
      },
      "+"
    ));
  }
  function TabOverview({ chatId }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const loadData = useCallback(() => {
      setLoading(true);
      setError(null);
      Api.getStats(chatId).then(setStats).catch((e) => setError(e.message)).finally(() => setLoading(false));
    }, [chatId]);
    useEffect(() => {
      loadData();
    }, [loadData]);
    if (loading) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-4" }, /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-2 gap-3" }, [1, 2, 3, 4].map((i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "skeleton-box h-24" }))), /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-44" }));
    }
    if (error) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-8 text-center flex flex-col items-center justify-center min-h-[300px]" }, /* @__PURE__ */ React.createElement("div", { className: "w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500 mb-3" }, Icons.alert("#e11d48", 22)), /* @__PURE__ */ React.createElement("p", { className: "text-sm font-bold text-slate-200 mb-1" }, "\u041E\u0448\u0438\u0431\u043A\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043A\u0438"), /* @__PURE__ */ React.createElement("p", { className: "text-xs text-slate-400 mb-4" }, error), /* @__PURE__ */ React.createElement("button", { onClick: loadData, className: "px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-xl text-slate-200" }, "\u041F\u043E\u0432\u0442\u043E\u0440\u0438\u0442\u044C \u0437\u0430\u043F\u0440\u043E\u0441"));
    }
    const total = stats?.total_violations || 0;
    const categories = stats?.violations_by_category || [];
    const accuracy = total > 0 ? ((1 - (stats?.false_positives_count || 0) / total) * 100).toFixed(1) : 100;
    const CAT_NAMES = {
      crypto_scam: "\u041A\u0440\u0438\u043F\u0442\u043E-\u0441\u043A\u0430\u043C / \u0424\u0438\u0448\u0438\u043D\u0433",
      ad: "\u0420\u0435\u043A\u043B\u0430\u043C\u0430 \u0438 \u0441\u043F\u0430\u043C-\u0441\u0441\u044B\u043B\u043A\u0438",
      nsfw: "NSFW / \u0417\u0430\u043F\u0440\u0435\u0449\u0435\u043D\u043D\u044B\u0435 \u043C\u0435\u0434\u0438\u0430",
      toxic: "\u041E\u0441\u043A\u043E\u0440\u0431\u043B\u0435\u043D\u0438\u044F / \u0422\u043E\u043A\u0441\u0438\u0447\u043D\u043E\u0441\u0442\u044C",
      flood: "\u0424\u043B\u0443\u0434 / \u0420\u0435\u0439\u0434 \u0430\u0442\u0430\u043A\u0438",
      cas: "\u0413\u043B\u043E\u0431\u0430\u043B\u044C\u043D\u044B\u0439 CAS \u0431\u0430\u043D"
    };
    const CAT_COLORS = {
      crypto_scam: "bg-rose-500",
      ad: "bg-amber-500",
      nsfw: "bg-purple-500",
      toxic: "bg-blue-500",
      flood: "bg-orange-500",
      cas: "bg-red-600"
    };
    return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-4 anim-fade" }, /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-2 gap-3" }, /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 flex flex-col justify-between" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-start" }, /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-semibold text-slate-400 uppercase tracking-wider" }, "\u0423\u0433\u0440\u043E\u0437\u044B"), /* @__PURE__ */ React.createElement("span", { className: "w-2 h-2 rounded-full bg-rose-500 shadow-sm shadow-rose-500" })), /* @__PURE__ */ React.createElement("div", { className: "mt-2" }, /* @__PURE__ */ React.createElement(AnimatedCounter, { value: total, colorClass: "text-white" }), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] text-slate-500 mt-1" }, "\u043D\u0435\u0439\u0442\u0440\u0430\u043B\u0438\u0437\u043E\u0432\u0430\u043D\u043E"))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 flex flex-col justify-between" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-start" }, /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-semibold text-slate-400 uppercase tracking-wider" }, "\u0411\u0430\u043D\u044B"), /* @__PURE__ */ React.createElement("span", { className: "w-2 h-2 rounded-full bg-rose-600" })), /* @__PURE__ */ React.createElement("div", { className: "mt-2" }, /* @__PURE__ */ React.createElement(AnimatedCounter, { value: stats?.total_bans || 0, colorClass: "text-rose-400" }), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] text-slate-500 mt-1" }, "\u043F\u0435\u0440\u043C\u0430\u043D\u0435\u043D\u0442\u043D\u043E"))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 flex flex-col justify-between" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-start" }, /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-semibold text-slate-400 uppercase tracking-wider" }, "\u0412\u0430\u0440\u043D\u044B"), /* @__PURE__ */ React.createElement("span", { className: "w-2 h-2 rounded-full bg-amber-400" })), /* @__PURE__ */ React.createElement("div", { className: "mt-2" }, /* @__PURE__ */ React.createElement(AnimatedCounter, { value: stats?.total_warns_issued || 0, colorClass: "text-amber-400" }), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] text-slate-500 mt-1" }, "\u043F\u0440\u0435\u0434\u0443\u043F\u0440\u0435\u0436\u0434\u0435\u043D\u0438\u0439"))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 flex flex-col justify-between" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-start" }, /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-semibold text-slate-400 uppercase tracking-wider" }, "\u0422\u043E\u0447\u043D\u043E\u0441\u0442\u044C \u0418\u0418"), /* @__PURE__ */ React.createElement("span", { className: "w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-500" })), /* @__PURE__ */ React.createElement("div", { className: "mt-2" }, /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-2xl font-bold tracking-tight text-emerald-400" }, accuracy, "%"), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] text-slate-500 mt-1" }, stats?.false_positives_count || 0, " \u043B\u043E\u0436\u043D\u044B\u0445")))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-3.5" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-200 uppercase tracking-wider" }, "\u0421\u0442\u0440\u0443\u043A\u0442\u0443\u0440\u0430 \u043D\u0430\u0440\u0443\u0448\u0435\u043D\u0438\u0439"), /* @__PURE__ */ React.createElement("span", { className: "text-[10px] font-mono-code text-slate-500" }, "24/7 Monitor")), categories.length > 0 ? /* @__PURE__ */ React.createElement("div", { className: "space-y-3" }, categories.map((cat, idx) => {
      const pct = total > 0 ? Math.round(cat.count / total * 100) : 0;
      return /* @__PURE__ */ React.createElement("div", { key: idx, className: "space-y-1" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between text-xs" }, /* @__PURE__ */ React.createElement("span", { className: "text-slate-300 font-medium" }, CAT_NAMES[cat.category] || cat.category), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-slate-400 text-[11px]" }, cat.count, " (", pct, "%)")), /* @__PURE__ */ React.createElement("div", { className: "h-1.5 w-full bg-[#181f2e] rounded-full overflow-hidden" }, /* @__PURE__ */ React.createElement(
        "div",
        {
          className: `h-full ${CAT_COLORS[cat.category] || "bg-rose-500"} rounded-full transition-all duration-700`,
          style: { width: `${pct}%` }
        }
      )));
    })) : /* @__PURE__ */ React.createElement("div", { className: "py-6 text-center text-xs text-slate-500" }, "\u0412 \u044D\u0442\u043E\u0439 \u0433\u0440\u0443\u043F\u043F\u0435 \u043F\u043E\u043A\u0430 \u043D\u0435\u0442 \u0437\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043E\u0432\u0430\u043D\u043D\u044B\u0445 \u043D\u0430\u0440\u0443\u0448\u0435\u043D\u0438\u0439.")));
  }
  function TabSettings({ chatId }) {
    const [settings, setSettings] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [saveToast, setSaveToast] = useState(false);
    const dirtyRef = useRef({});
    const loadSettings = useCallback(() => {
      setLoading(true);
      setError(null);
      Api.getSettings(chatId).then((data) => {
        setSettings(data);
        dirtyRef.current = {};
      }).catch((e) => setError(e.message)).finally(() => setLoading(false));
    }, [chatId]);
    useEffect(() => {
      loadSettings();
    }, [loadSettings]);
    const updateField = (key, value) => {
      setSettings((prev) => {
        const next = { ...prev, [key]: value };
        dirtyRef.current[key] = value;
        return next;
      });
    };
    const hasChanges = Object.keys(dirtyRef.current).length > 0;
    useEffect(() => {
      const tg = window.Telegram?.WebApp;
      if (!tg?.MainButton) return;
      if (hasChanges) {
        tg.MainButton.setText("\u0421\u041E\u0425\u0420\u0410\u041D\u0418\u0422\u042C \u0418\u0417\u041C\u0415\u041D\u0415\u041D\u0418\u042F");
        tg.MainButton.color = "#e11d48";
        tg.MainButton.textColor = "#ffffff";
        tg.MainButton.show();
      } else {
        tg.MainButton.hide();
      }
      const handleMainButtonClick = () => {
        executeSave();
      };
      tg.MainButton.onClick(handleMainButtonClick);
      return () => {
        tg.MainButton.offClick(handleMainButtonClick);
      };
    }, [hasChanges, settings]);
    const executeSave = async () => {
      if (!hasChanges) return;
      setSaving(true);
      try {
        const updated = await Api.saveSettings(chatId, dirtyRef.current);
        setSettings(updated);
        dirtyRef.current = {};
        setSaveToast(true);
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("success");
        window.Telegram?.WebApp?.MainButton?.hide();
        setTimeout(() => setSaveToast(false), 2500);
      } catch (err) {
        alert("\u041E\u0448\u0438\u0431\u043A\u0430 \u043F\u0440\u0438 \u0441\u043E\u0445\u0440\u0430\u043D\u0435\u043D\u0438\u0438: " + err.message);
      } finally {
        setSaving(false);
      }
    };
    if (loading) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-3" }, /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-24" }), /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-48" }), /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-48" }));
    }
    if (error || !settings) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-8 text-center flex flex-col items-center justify-center" }, /* @__PURE__ */ React.createElement("p", { className: "text-xs text-rose-400 mb-3" }, error || "\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u043D\u044B"), /* @__PURE__ */ React.createElement("button", { onClick: loadSettings, className: "px-4 py-2 bg-slate-800 text-xs font-semibold rounded-xl" }, "\u041F\u043E\u0432\u0442\u043E\u0440\u0438\u0442\u044C"));
    }
    return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-4 pb-32 anim-fade" }, /* @__PURE__ */ React.createElement("div", { className: `p-3.5 rounded-2xl border transition-all flex items-center justify-between gap-3 ${hasChanges ? "bg-rose-950/20 border-rose-500/40 shadow-lg shadow-rose-950/30" : "bg-[#0d111a] border-[#1a2233]"}` }, /* @__PURE__ */ React.createElement("div", { className: "min-w-0" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-2" }, /* @__PURE__ */ React.createElement("span", { className: `w-2 h-2 rounded-full ${hasChanges ? "bg-rose-500 animate-ping" : "bg-emerald-400"}` }), /* @__PURE__ */ React.createElement("p", { className: "text-xs font-bold text-slate-200" }, hasChanges ? "\u0415\u0441\u0442\u044C \u043D\u0435\u0441\u043E\u0445\u0440\u0430\u043D\u0451\u043D\u043D\u044B\u0435 \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u044F" : "\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 \u0430\u043A\u0442\u0443\u0430\u043B\u044C\u043D\u044B")), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400 mt-0.5 truncate" }, hasChanges ? "\u041D\u0430\u0436\u043C\u0438\u0442\u0435 \u0421\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C \u0434\u043B\u044F \u043F\u0440\u0438\u043C\u0435\u043D\u0435\u043D\u0438\u044F" : "\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0438\u0440\u043E\u0432\u0430\u043D\u043E \u0441 \u0431\u0430\u0437\u043E\u0439 \u0434\u0430\u043D\u043D\u044B\u0445")), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: executeSave,
        disabled: saving || !hasChanges,
        className: `shrink-0 px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 ${hasChanges ? "bg-[#e11d48] hover:bg-[#be123c] active:scale-95 text-white shadow-lg shadow-rose-950/80" : "bg-slate-800/60 text-slate-500 cursor-not-allowed"}`
      },
      saving ? "\u0421\u043E\u0445\u0440\u0430\u043D\u044F\u044E..." : hasChanges ? "\u0421\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C" : "\u0413\u043E\u0442\u043E\u0432\u043E"
    )), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-4" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "\u041C\u043E\u0434\u0435\u0440\u0430\u0446\u0438\u044F \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0439"), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-[11px] font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-lg border border-rose-500/20" }, settings.moderation_mode === "ai_judge" ? "\u0410\u0412\u0422\u041E-\u0420\u0415\u0416\u0418\u041C" : settings.moderation_mode === "review_only" ? "\u0420\u0415\u0416\u0418\u041C: \u041D\u0410 \u0420\u0410\u0421\u0421\u041C\u041E\u0422\u0420\u0415\u041D\u0418\u0415" : settings.moderation_mode === "strict_confidence" ? "\u0420\u0415\u0416\u0418\u041C: \u0411\u0410\u041D 95%+" : `\u0411\u0430\u043D: ${Math.round(settings.ai_confidence_threshold || 85)}%`)), /* @__PURE__ */ React.createElement("div", { className: "space-y-2" }, /* @__PURE__ */ React.createElement("p", { className: "text-[11px] font-semibold text-slate-300" }, "\u0420\u0435\u0436\u0438\u043C \u043F\u0440\u0438\u043D\u044F\u0442\u0438\u044F \u0440\u0435\u0448\u0435\u043D\u0438\u0439:"), /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-2 gap-2" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        onClick: () => updateField("moderation_mode", "ai_judge"),
        className: `p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${(settings.moderation_mode || "ai_judge") === "ai_judge" ? "bg-rose-500/20 border-rose-500 text-white shadow-md shadow-rose-950/60" : "bg-[#07090e] border-[#1a2233] text-slate-400 hover:text-slate-200"}`
      },
      /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-bold flex items-center gap-1" }, "\u26A1 \u0410\u0432\u0442\u043E-\u043E\u0446\u0435\u043D\u043A\u0430"),
      /* @__PURE__ */ React.createElement("span", { className: "text-[9px] text-slate-400 leading-tight mt-1" }, "\u0411\u043E\u0442 \u0441\u0430\u043C \u043F\u043E\u0434\u0431\u0438\u0440\u0430\u0435\u0442 \u0441\u043E\u0440\u0430\u0437\u043C\u0435\u0440\u043D\u043E\u0435 \u043D\u0430\u043A\u0430\u0437\u0430\u043D\u0438\u0435 \u043F\u043E \u043A\u043E\u043D\u0442\u0435\u043A\u0441\u0442\u0443")
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        onClick: () => updateField("moderation_mode", "standard"),
        className: `p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${settings.moderation_mode === "standard" ? "bg-rose-500/20 border-rose-500 text-white shadow-md shadow-rose-950/60" : "bg-[#07090e] border-[#1a2233] text-slate-400 hover:text-slate-200"}`
      },
      /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-bold" }, "\u{1F4CA} \u041F\u043E \u0448\u043A\u0430\u043B\u0435 \u0440\u0438\u0441\u043A\u0430"),
      /* @__PURE__ */ React.createElement("span", { className: "text-[9px] text-slate-400 leading-tight mt-1" }, "\u041D\u0430\u0441\u0442\u0440\u0430\u0438\u0432\u0430\u0435\u043C\u044B\u0435 \u043F\u0440\u043E\u0446\u0435\u043D\u0442\u044B \u0434\u043B\u044F \u043F\u0440\u043E\u043F\u0443\u0441\u043A\u0430, \u0432\u0430\u0440\u043D\u0430 \u0438 \u0431\u0430\u043D\u0430")
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        onClick: () => updateField("moderation_mode", "review_only"),
        className: `p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${settings.moderation_mode === "review_only" ? "bg-amber-500/20 border-amber-500 text-white shadow-md shadow-amber-950/60" : "bg-[#07090e] border-[#1a2233] text-slate-400 hover:text-slate-200"}`
      },
      /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-bold text-amber-300" }, "\u{1F6E1}\uFE0F \u0411\u0435\u0437 \u0430\u0432\u0442\u043E-\u0431\u0430\u043D\u0430"),
      /* @__PURE__ */ React.createElement("span", { className: "text-[9px] text-slate-400 leading-tight mt-1" }, "\u0422\u043E\u043B\u044C\u043A\u043E \u0432\u0430\u0440\u043D\u044B \u0438 \u0443\u0434\u0430\u043B\u0435\u043D\u0438\u0435. \u0411\u0435\u0437 \u0430\u0432\u0442\u043E\u043C\u0430\u0442\u0438\u0447\u0435\u0441\u043A\u0438\u0445 \u0431\u0430\u043D\u043E\u0432")
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        onClick: () => updateField("moderation_mode", "strict_confidence"),
        className: `p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${settings.moderation_mode === "strict_confidence" ? "bg-indigo-500/20 border-indigo-500 text-white shadow-md shadow-indigo-950/60" : "bg-[#07090e] border-[#1a2233] text-slate-400 hover:text-slate-200"}`
      },
      /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-bold text-indigo-300" }, "\u{1F3AF} \u041C\u0430\u043A\u0441. \u0441\u0442\u0440\u043E\u0433\u043E\u0441\u0442\u044C"),
      /* @__PURE__ */ React.createElement("span", { className: "text-[9px] text-slate-400 leading-tight mt-1" }, "\u0411\u0430\u043D \u0442\u043E\u043B\u044C\u043A\u043E \u043F\u0440\u0438 100% \u043F\u043E\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043D\u043D\u043E\u043C \u0441\u043F\u0430\u043C\u0435")
    ))), /* @__PURE__ */ React.createElement("div", { className: "space-y-3 pt-2 border-t border-[#1a2233]" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("p", { className: "text-[11px] font-bold text-slate-200 uppercase tracking-wider" }, "\u0420\u0435\u0430\u043A\u0446\u0438\u044F \u043D\u0430 \u043D\u0430\u0440\u0443\u0448\u0435\u043D\u0438\u044F:"), /* @__PURE__ */ React.createElement("span", { className: "text-[10px] text-rose-400 font-mono-code" }, "\u0418\u043D\u0434\u0438\u0432\u0438\u0434\u0443\u0430\u043B\u044C\u043D\u043E")), /* @__PURE__ */ React.createElement("div", { className: "p-3 bg-[#07090e] rounded-xl border border-[#1a2233] space-y-2" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-bold text-slate-200" }, "\u041E\u0441\u043A\u043E\u0440\u0431\u043B\u0435\u043D\u0438\u044F \u0438 \u0430\u0433\u0440\u0435\u0441\u0441\u0438\u044F"), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] text-slate-400" }, "\u041F\u0440\u044F\u043C\u044B\u0435 \u043E\u0441\u043A\u043E\u0440\u0431\u043B\u0435\u043D\u0438\u044F \u0443\u0447\u0430\u0441\u0442\u043D\u0438\u043A\u043E\u0432, \u043C\u0430\u0442 \u0438 \u0442\u0440\u0430\u0432\u043B\u044F")), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300" }, (settings.category_actions || {}).toxic_insult === "ignore" ? "\u041D\u0415 \u0422\u0420\u041E\u0413\u0410\u0422\u042C" : (settings.category_actions || {}).toxic_insult === "delete" ? "\u0423\u0414\u0410\u041B\u0418\u0422\u042C" : (settings.category_actions || {}).toxic_insult === "mute" ? "\u041C\u0423\u0422" : (settings.category_actions || {}).toxic_insult === "ban" ? "\u0411\u0410\u041D" : (settings.category_actions || {}).toxic_insult === "warn" ? "\u0412\u0410\u0420\u041D" : "\u0410\u0412\u0422\u041E")), /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-3 gap-1 text-[10px] font-semibold" }, [
      { id: "ai_default", label: "\u26A1 \u0410\u0432\u0442\u043E" },
      { id: "ignore", label: "\u041D\u0435 \u0442\u0440\u043E\u0433\u0430\u0442\u044C" },
      { id: "delete", label: "\u0423\u0434\u0430\u043B\u0438\u0442\u044C" },
      { id: "warn", label: "\u0412\u0430\u0440\u043D" },
      { id: "mute", label: "\u041C\u0443\u0442" },
      { id: "ban", label: "\u0411\u0430\u043D" }
    ].map((act) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: act.id,
        type: "button",
        onClick: () => {
          const cur = { ...settings.category_actions || {} };
          cur.toxic_insult = act.id;
          updateField("category_actions", cur);
        },
        className: `py-1.5 px-2 rounded-lg border transition-all ${((settings.category_actions || {}).toxic_insult || "ai_default") === act.id ? "bg-rose-500 text-white border-rose-500 font-bold" : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200"}`
      },
      act.label
    )))), /* @__PURE__ */ React.createElement("div", { className: "p-3 bg-[#07090e] rounded-xl border border-[#1a2233] space-y-2" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-bold text-slate-200" }, "\u0420\u0435\u043A\u043B\u0430\u043C\u0430 \u0438 \u043F\u0440\u043E\u043C\u043E-\u0441\u0441\u044B\u043B\u043A\u0438"), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] text-slate-400" }, "\u0421\u0441\u044B\u043B\u043A\u0438 \u043D\u0430 \u043A\u0430\u043D\u0430\u043B\u044B, \u0431\u043E\u0442\u043E\u0432, \u043D\u0435\u0441\u0430\u043D\u043A\u0446\u0438\u043E\u043D\u0438\u0440\u043E\u0432\u0430\u043D\u043D\u044B\u0439 \u043F\u0438\u0430\u0440")), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300" }, (settings.category_actions || {}).commercial_ad === "ignore" ? "\u041D\u0415 \u0422\u0420\u041E\u0413\u0410\u0422\u042C" : (settings.category_actions || {}).commercial_ad === "delete" ? "\u0423\u0414\u0410\u041B\u0418\u0422\u042C" : (settings.category_actions || {}).commercial_ad === "mute" ? "\u041C\u0423\u0422" : (settings.category_actions || {}).commercial_ad === "ban" ? "\u0411\u0410\u041D" : (settings.category_actions || {}).commercial_ad === "warn" ? "\u0412\u0410\u0420\u041D" : "\u0410\u0412\u0422\u041E")), /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-3 gap-1 text-[10px] font-semibold" }, [
      { id: "ai_default", label: "\u26A1 \u0410\u0432\u0442\u043E" },
      { id: "ignore", label: "\u041D\u0435 \u0442\u0440\u043E\u0433\u0430\u0442\u044C" },
      { id: "delete", label: "\u0423\u0434\u0430\u043B\u0438\u0442\u044C" },
      { id: "warn", label: "\u0412\u0430\u0440\u043D" },
      { id: "mute", label: "\u041C\u0443\u0442" },
      { id: "ban", label: "\u0411\u0430\u043D" }
    ].map((act) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: act.id,
        type: "button",
        onClick: () => {
          const cur = { ...settings.category_actions || {} };
          cur.commercial_ad = act.id;
          updateField("category_actions", cur);
        },
        className: `py-1.5 px-2 rounded-lg border transition-all ${((settings.category_actions || {}).commercial_ad || "ai_default") === act.id ? "bg-rose-500 text-white border-rose-500 font-bold" : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200"}`
      },
      act.label
    )))), /* @__PURE__ */ React.createElement("div", { className: "p-3 bg-[#07090e] rounded-xl border border-[#1a2233] space-y-2" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-bold text-slate-200" }, "\u041C\u043E\u0448\u0435\u043D\u043D\u0438\u0447\u0435\u0441\u0442\u0432\u043E \u0438 \u0441\u043A\u0430\u043C"), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] text-slate-400" }, "\u0424\u0435\u0439\u043A\u043E\u0432\u044B\u0435 \u0440\u0430\u0437\u0434\u0430\u0447\u0438, \u0441\u043F\u0430\u043C-\u0431\u043E\u0442\u044B, \u0432\u0440\u0435\u0434\u043E\u043D\u043E\u0441\u043D\u044B\u0435 \u0441\u0441\u044B\u043B\u043A\u0438")), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold" }, (settings.category_actions || {}).crypto_scam === "warn" ? "\u0412\u0410\u0420\u041D" : (settings.category_actions || {}).crypto_scam === "mute" ? "\u041C\u0423\u0422" : "\u0411\u0410\u041D")), /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-3 gap-1 text-[10px] font-semibold" }, [
      { id: "ban", label: "\u0411\u0430\u043D" },
      { id: "mute", label: "\u041C\u0443\u0442" },
      { id: "warn", label: "\u0412\u0430\u0440\u043D" }
    ].map((act) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: act.id,
        type: "button",
        onClick: () => {
          const cur = { ...settings.category_actions || {} };
          cur.crypto_scam = act.id;
          updateField("category_actions", cur);
        },
        className: `py-1.5 px-2 rounded-lg border transition-all ${((settings.category_actions || {}).crypto_scam || "ban") === act.id ? "bg-rose-500 text-white border-rose-500 font-bold" : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200"}`
      },
      act.label
    ))))), settings.moderation_mode === "standard" && /* @__PURE__ */ React.createElement("div", { className: "space-y-3 pt-2 border-t border-[#1a2233]" }, /* @__PURE__ */ React.createElement("div", { className: "space-y-1 pt-1" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between text-[11px]" }, /* @__PURE__ */ React.createElement("span", { className: "text-slate-300 font-semibold" }, "\u041F\u043E\u0440\u043E\u0433 \u0430\u0432\u0442\u043E-\u0431\u0430\u043D\u0430"), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-rose-400 font-bold" }, Math.round(settings.ai_confidence_threshold || 85), "%")), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "range",
        min: "60",
        max: "98",
        value: settings.ai_confidence_threshold || 85,
        onChange: (e) => updateField("ai_confidence_threshold", Number(e.target.value))
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "space-y-1 pt-1" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between text-[11px]" }, /* @__PURE__ */ React.createElement("span", { className: "text-slate-300 font-semibold" }, "\u041F\u043E\u0440\u043E\u0433 \u043F\u0440\u043E\u0432\u0435\u0440\u043A\u0438 \u0438 \u043F\u0440\u0435\u0434\u0443\u043F\u0440\u0435\u0436\u0434\u0435\u043D\u0438\u0439"), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-amber-400 font-bold" }, Math.round(settings.ai_review_threshold || 50), "%")), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "range",
        min: "25",
        max: "75",
        value: settings.ai_review_threshold || 50,
        onChange: (e) => updateField("ai_review_threshold", Number(e.target.value))
      }
    ))), /* @__PURE__ */ React.createElement("div", { className: "divide-y divide-[#1a2233] pt-1" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0410\u0432\u0442\u043E\u043C\u0430\u0442\u0438\u0447\u0435\u0441\u043A\u0430\u044F \u0444\u0438\u043B\u044C\u0442\u0440\u0430\u0446\u0438\u044F"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0410\u043D\u0430\u043B\u0438\u0437 \u0442\u0435\u043A\u0441\u0442\u0430 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0439 \u043D\u0430 \u0441\u043F\u0430\u043C \u0438 \u0443\u0433\u0440\u043E\u0437\u044B")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.ai_moderation_enabled,
        onChange: (e) => updateField("ai_moderation_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-1.5" }, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0421\u043F\u043E\u0440\u043D\u044B\u0435 \u0421\u041C\u0421 \u043D\u0430 \u043F\u0440\u043E\u0432\u0435\u0440\u043A\u0443 \u0430\u0434\u043C\u0438\u043D\u0430\u043C"), /* @__PURE__ */ React.createElement("span", { className: "text-[9px] font-mono-code text-amber-400 bg-amber-500/10 px-1 rounded border border-amber-500/20" }, "\u0418\u043D\u0442\u0435\u0440\u0430\u043A\u0442\u0438\u0432\u043D\u044B\u0435 \u043A\u043D\u043E\u043F\u043A\u0438")), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u041E\u0442\u043F\u0440\u0430\u0432\u043B\u044F\u0442\u044C \u043A\u0430\u0440\u0442\u043E\u0447\u043A\u0438 \u0441 \u043A\u043D\u043E\u043F\u043A\u0430\u043C\u0438 [\u0417\u0430\u0431\u0430\u043D\u0438\u0442\u044C / \u041E\u0434\u043E\u0431\u0440\u0438\u0442\u044C / \u041C\u0443\u0442] \u043F\u0440\u0438 \u0441\u043E\u043C\u043D\u0435\u043D\u0438\u044F\u0445 \u0418\u0418")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.send_suspicious_to_admin !== false,
        onChange: (e) => updateField("send_suspicious_to_admin", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "py-3 flex items-center justify-between" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u041E\u0431\u0440\u0430\u0431\u043E\u0442\u043A\u0430 \u0436\u0430\u043B\u043E\u0431 (/report)"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u041A\u0443\u0434\u0430 \u043D\u0430\u043F\u0440\u0430\u0432\u043B\u044F\u0442\u044C \u0436\u0430\u043B\u043E\u0431\u044B \u0443\u0447\u0430\u0441\u0442\u043D\u0438\u043A\u043E\u0432")), /* @__PURE__ */ React.createElement(
      SegmentedControl,
      {
        options: [
          { value: "admin_only", label: "\u0410\u0434\u043C\u0438\u043D\u0430\u043C" },
          { value: "ai_instant", label: "\u041D\u0435\u0439\u0440\u043E\u0441\u0435\u0442\u0438" }
        ],
        value: settings.report_mode || "admin_only",
        onChange: (v) => updateField("report_mode", v)
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-1.5" }, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-rose-300" }, "\u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0430 \u043A\u0430\u0436\u0434\u043E\u0433\u043E \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u044F"), /* @__PURE__ */ React.createElement("span", { className: "text-[9px] font-mono-code text-rose-400 bg-rose-500/10 px-1 rounded border border-rose-500/20" }, "\u0412\u0441\u0435 \u043F\u043E\u0434\u0440\u044F\u0434")), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0421\u043A\u0430\u043D\u0438\u0440\u043E\u0432\u0430\u0442\u044C 100% \u0432\u0445\u043E\u0434\u044F\u0449\u0438\u0445 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0439 \u043F\u043E\u0434\u0440\u044F\u0434")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.full_scan_enabled || false,
        onChange: (e) => updateField("full_scan_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "CAS \u0411\u0430\u043D-\u043B\u0438\u0441\u0442"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0413\u043B\u043E\u0431\u0430\u043B\u044C\u043D\u0430\u044F \u0431\u0430\u0437\u0430 \u0438\u0437\u0432\u0435\u0441\u0442\u043D\u044B\u0445 \u0441\u043F\u0430\u043C\u0435\u0440\u043E\u0432")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.cas_check_enabled,
        onChange: (e) => updateField("cas_check_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-3" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "\u041A\u043E\u043D\u0442\u0440\u043E\u043B\u044C \u0443\u0447\u0430\u0441\u0442\u043D\u0438\u043A\u043E\u0432"), /* @__PURE__ */ React.createElement("div", { className: "divide-y divide-[#1a2233]" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0430 \u043F\u0440\u0438 \u0432\u0445\u043E\u0434\u0435 (\u041A\u0430\u043F\u0447\u0430)"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0417\u0430\u0449\u0438\u0442\u0430 \u043E\u0442 \u043D\u0430\u043F\u043B\u044B\u0432\u0430 \u0441\u043F\u0430\u043C-\u0431\u043E\u0442\u043E\u0432")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.captcha_enabled,
        onChange: (e) => updateField("captcha_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), settings.captcha_enabled && /* @__PURE__ */ React.createElement("div", { className: "py-3 flex items-center justify-between" }, /* @__PURE__ */ React.createElement("span", { className: "text-xs text-slate-400" }, "\u0422\u0438\u043F \u0432\u0435\u0440\u0438\u0444\u0438\u043A\u0430\u0446\u0438\u0438:"), /* @__PURE__ */ React.createElement(
      SegmentedControl,
      {
        options: [
          { value: "button", label: "\u041A\u043D\u043E\u043F\u043A\u0430" },
          { value: "ai_profiling", label: "\u0423\u043C\u043D\u0430\u044F" }
        ],
        value: settings.captcha_type || "button",
        onChange: (v) => updateField("captcha_type", v)
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0410\u043D\u0442\u0438-\u0440\u0435\u0439\u0434 \u0437\u0430\u0449\u0438\u0442\u0430"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u041B\u043E\u043A\u0434\u0430\u0443\u043D \u043F\u0440\u0438 \u043D\u0430\u043F\u043B\u044B\u0432\u0435 >8 \u0432\u0445\u043E\u0434\u043E\u0432/15\u0441")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.anti_raid_enabled,
        onChange: (e) => updateField("anti_raid_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u041E\u0433\u0440\u0430\u043D\u0438\u0447\u0435\u043D\u0438\u0435 \u0434\u043B\u044F \u043D\u043E\u0432\u0438\u0447\u043A\u043E\u0432"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0417\u0430\u043F\u0440\u0435\u0442 \u043C\u0435\u0434\u0438\u0430\u0444\u0430\u0439\u043B\u043E\u0432 \u0432 \u043F\u0435\u0440\u0432\u044B\u0435 \u0447\u0430\u0441\u044B \u043F\u043E\u0441\u043B\u0435 \u0432\u0445\u043E\u0434\u0430")), /* @__PURE__ */ React.createElement(
      StepperControl,
      {
        value: settings.newbie_media_lock_hours || 0,
        min: 0,
        max: 72,
        suffix: "\u0447",
        onChange: (v) => updateField("newbie_media_lock_hours", v)
      }
    )))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-3" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "\u041F\u0440\u0430\u0432\u0438\u043B\u0430 \u043A\u043E\u043D\u0442\u0435\u043D\u0442\u0430"), /* @__PURE__ */ React.createElement("div", { className: "divide-y divide-[#1a2233]" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0421\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u044F \u043E\u0442 \u043A\u0430\u043D\u0430\u043B\u043E\u0432"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0411\u043B\u043E\u043A\u0438\u0440\u043E\u0432\u0430\u0442\u044C \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u044F \u043E\u0442 \u0438\u043C\u0435\u043D\u0438 \u043A\u0430\u043D\u0430\u043B\u043E\u0432")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: !settings.allow_sender_chat,
        onChange: (e) => updateField("allow_sender_chat", !e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0418\u043D\u043B\u0430\u0439\u043D-\u0431\u043E\u0442\u044B"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0420\u0430\u0437\u0440\u0435\u0448\u0438\u0442\u044C \u043E\u0442\u043F\u0440\u0430\u0432\u043A\u0443 \u0447\u0435\u0440\u0435\u0437 \u0432\u043D\u0435\u0448\u043D\u0438\u0445 \u0431\u043E\u0442\u043E\u0432")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.allow_via_bot,
        onChange: (e) => updateField("allow_via_bot", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0421\u043B\u0443\u0436\u0435\u0431\u043D\u044B\u0435 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u044F"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0423\u0434\u0430\u043B\u044F\u0442\u044C \xAB\u0432\u0441\u0442\u0443\u043F\u0438\u043B\xBB, \xAB\u0437\u0430\u043A\u0440\u0435\u043F\u0438\u043B\xBB, \xAB\u043F\u043E\u043A\u0438\u043D\u0443\u043B\xBB")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.clean_service_messages,
        onChange: (e) => updateField("clean_service_messages", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-3" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "\u041C\u0435\u0434\u0438\u0430-\u0444\u0438\u043B\u044C\u0442\u0440\u044B"), /* @__PURE__ */ React.createElement("span", { className: "text-[10px] font-mono-code text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20" }, "\u041B\u043E\u043A\u0430\u043B\u044C\u043D\u043E")), /* @__PURE__ */ React.createElement("div", { className: "divide-y divide-[#1a2233]" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0424\u0438\u043B\u044C\u0442\u0440 18+ \u043A\u043E\u043D\u0442\u0435\u043D\u0442\u0430"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0424\u043E\u0442\u043E, \u0432\u0438\u0434\u0435\u043E, \u043A\u0440\u0443\u0436\u043E\u0447\u043A\u0438 \u0438 \u0441\u0442\u0438\u043A\u0435\u0440\u044B")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.media_nsfw_filter_enabled ?? true,
        onChange: (e) => updateField("media_nsfw_filter_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0422\u0435\u043A\u0441\u0442 \u043D\u0430 \u0438\u0437\u043E\u0431\u0440\u0430\u0436\u0435\u043D\u0438\u044F\u0445"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0420\u0430\u0441\u043F\u043E\u0437\u043D\u0430\u0432\u0430\u043D\u0438\u0435 \u0441\u043F\u0430\u043C-\u0442\u0435\u043A\u0441\u0442\u0430 \u0438 \u0441\u0441\u044B\u043B\u043E\u043A \u0441\u043E \u0441\u043A\u0440\u0438\u043D\u0448\u043E\u0442\u043E\u0432")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.media_ocr_filter_enabled ?? true,
        onChange: (e) => updateField("media_ocr_filter_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0421\u043A\u0430\u043D\u0435\u0440 QR-\u043A\u043E\u0434\u043E\u0432"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0430 \u0441\u0441\u044B\u043B\u043E\u043A \u0432\u043D\u0443\u0442\u0440\u0438 QR-\u0438\u0437\u043E\u0431\u0440\u0430\u0436\u0435\u043D\u0438\u0439")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.media_qr_filter_enabled ?? true,
        onChange: (e) => updateField("media_qr_filter_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-3" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "\u0421\u0438\u0441\u0442\u0435\u043C\u0430 \u043D\u0430\u043A\u0430\u0437\u0430\u043D\u0438\u0439"), /* @__PURE__ */ React.createElement("div", { className: "divide-y divide-[#1a2233]" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u041B\u0438\u043C\u0438\u0442 \u043F\u0440\u0435\u0434\u0443\u043F\u0440\u0435\u0436\u0434\u0435\u043D\u0438\u0439"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u041A\u043E\u043B\u0438\u0447\u0435\u0441\u0442\u0432\u043E \u0432\u0430\u0440\u043D\u043E\u0432 \u0434\u043E \u043D\u0430\u043A\u0430\u0437\u0430\u043D\u0438\u044F")), /* @__PURE__ */ React.createElement(
      StepperControl,
      {
        value: settings.warn_limit || 3,
        min: 1,
        max: 10,
        onChange: (v) => updateField("warn_limit", v)
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0421\u0440\u043E\u043A \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044F \u0432\u0430\u0440\u043D\u043E\u0432"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0410\u0432\u0442\u043E-\u0441\u0433\u043E\u0440\u0430\u043D\u0438\u0435 \u043F\u0440\u0435\u0434\u0443\u043F\u0440\u0435\u0436\u0434\u0435\u043D\u0438\u0439 \u0447\u0435\u0440\u0435\u0437 N \u0434\u043D\u0435\u0439")), /* @__PURE__ */ React.createElement(
      StepperControl,
      {
        value: settings.warn_expiration_days || 7,
        min: 1,
        max: 90,
        suffix: "\u0434",
        onChange: (v) => updateField("warn_expiration_days", v)
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "py-3 flex items-center justify-between" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u041D\u0430\u043A\u0430\u0437\u0430\u043D\u0438\u0435"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u043F\u0440\u0438 \u043F\u0440\u0435\u0432\u044B\u0448\u0435\u043D\u0438\u0438")), /* @__PURE__ */ React.createElement(
      SegmentedControl,
      {
        options: [
          { value: "mute", label: "\u041C\u0443\u0442" },
          { value: "ban", label: "\u0411\u0430\u043D" },
          { value: "kick", label: "\u041A\u0438\u043A" }
        ],
        value: settings.warn_punishment || "mute",
        onChange: (v) => updateField("warn_punishment", v)
      }
    )), settings.warn_punishment === "mute" && /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0414\u043B\u0438\u0442\u0435\u043B\u044C\u043D\u043E\u0441\u0442\u044C \u043C\u0443\u0442\u0430"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u0412 \u043C\u0438\u043D\u0443\u0442\u0430\u0445")), /* @__PURE__ */ React.createElement(
      StepperControl,
      {
        value: settings.warn_mute_duration_minutes || 1440,
        min: 10,
        max: 10080,
        step: 60,
        suffix: "\u043C",
        onChange: (v) => updateField("warn_mute_duration_minutes", v)
      }
    )))), /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-3" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "\u041D\u043E\u0447\u043D\u043E\u0439 \u0440\u0435\u0436\u0438\u043C (\u0422\u0438\u0445\u0438\u0439 \u0447\u0430\u0441)"), /* @__PURE__ */ React.createElement("div", { className: "divide-y divide-[#1a2233]" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between py-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("p", { className: "text-xs font-semibold text-slate-200" }, "\u0412\u043A\u043B\u044E\u0447\u0438\u0442\u044C \u0442\u0438\u0445\u0438\u0439 \u0447\u0430\u0441"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, "\u041E\u0433\u0440\u0430\u043D\u0438\u0447\u0435\u043D\u0438\u0435 \u043E\u0442\u043F\u0440\u0430\u0432\u043A\u0438 \u043D\u043E\u0447\u044C\u044E")), /* @__PURE__ */ React.createElement("label", { className: "ios-switch" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: settings.night_mode_enabled,
        onChange: (e) => updateField("night_mode_enabled", e.target.checked)
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "ios-slider" }))), settings.night_mode_enabled && /* @__PURE__ */ React.createElement("div", { className: "py-3 grid grid-cols-2 gap-3" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "text-[10px] uppercase font-bold text-slate-400 mb-1 block" }, "\u041D\u0430\u0447\u0430\u043B\u043E"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "time",
        value: settings.night_mode_start || "23:00",
        onChange: (e) => updateField("night_mode_start", e.target.value),
        className: "w-full bg-[#07090e] border border-[#1e2738] rounded-xl px-3 py-2 text-xs font-mono-code text-white outline-none focus:border-rose-500"
      }
    )), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "text-[10px] uppercase font-bold text-slate-400 mb-1 block" }, "\u041A\u043E\u043D\u0435\u0446"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "time",
        value: settings.night_mode_end || "08:00",
        onChange: (e) => updateField("night_mode_end", e.target.value),
        className: "w-full bg-[#07090e] border border-[#1e2738] rounded-xl px-3 py-2 text-xs font-mono-code text-white outline-none focus:border-rose-500"
      }
    ))))), saveToast && /* @__PURE__ */ React.createElement("div", { className: "fixed bottom-20 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-4 py-2 rounded-full shadow-lg z-50 flex items-center gap-2 anim-fade" }, Icons.check("#ffffff", 14), " \u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 \u0443\u0441\u043F\u0435\u0448\u043D\u043E \u0441\u043E\u0445\u0440\u0430\u043D\u0435\u043D\u044B \u0432 \u0431\u0430\u0437\u0435 \u0434\u0430\u043D\u043D\u044B\u0445!"));
  }
  function TabLogs({ chatId }) {
    const [logs, setLogs] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const loadLogs = useCallback(() => {
      setLoading(true);
      setError(null);
      Api.getLogs(chatId, 50).then(setLogs).catch((e) => setError(e.message)).finally(() => setLoading(false));
    }, [chatId]);
    useEffect(() => {
      loadLogs();
    }, [loadLogs]);
    function formatTimeAgo(dateStr) {
      const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1e3);
      if (diff < 60) return `${diff}\u0441 \u043D\u0430\u0437\u0430\u0434`;
      if (diff < 3600) return `${Math.floor(diff / 60)}\u043C \u043D\u0430\u0437\u0430\u0434`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}\u0447 \u043D\u0430\u0437\u0430\u0434`;
      return `${Math.floor(diff / 86400)}\u0434 \u043D\u0430\u0437\u0430\u0434`;
    }
    const ACTION_LABELS = {
      delete: "\u0423\u0434\u0430\u043B\u0435\u043D\u043E",
      warn: "\u041F\u0440\u0435\u0434\u0443\u043F\u0440\u0435\u0436\u0434\u0435\u043D\u0438\u0435",
      mute: "\u0417\u0430\u043C\u0443\u0447\u0435\u043D",
      ban: "\u0417\u0430\u0431\u043B\u043E\u043A\u0438\u0440\u043E\u0432\u0430\u043D",
      kick: "\u0418\u0441\u043A\u043B\u044E\u0447\u0435\u043D",
      captcha_kick: "\u041A\u0430\u043F\u0447\u0430-\u041A\u0438\u043A",
      ban_user: "\u0417\u0430\u0431\u0430\u043D\u0435\u043D",
      mute_user: "\u0417\u0430\u043C\u0443\u0447\u0435\u043D"
    };
    const CAT_BADGES = {
      crypto_scam: "bg-rose-500/10 text-rose-400 border-rose-500/20",
      ad: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      nsfw: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      toxic: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      flood: "bg-orange-500/10 text-orange-400 border-orange-500/20",
      cas: "bg-red-500/10 text-red-400 border-red-500/20"
    };
    if (loading) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-3" }, [1, 2, 3, 4].map((i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "skeleton-box h-24" })));
    }
    if (error) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-8 text-center flex flex-col items-center justify-center" }, /* @__PURE__ */ React.createElement("p", { className: "text-xs text-rose-400 mb-3" }, error), /* @__PURE__ */ React.createElement("button", { onClick: loadLogs, className: "px-4 py-2 bg-slate-800 text-xs font-semibold rounded-xl" }, "\u041F\u043E\u0432\u0442\u043E\u0440\u0438\u0442\u044C"));
    }
    if (!logs || logs.length === 0) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-6 flex flex-col items-center justify-center min-h-[380px] text-center anim-fade" }, /* @__PURE__ */ React.createElement("div", { className: "w-16 h-16 rounded-3xl bg-[#0d111a] border border-[#1a2233] flex items-center justify-center text-rose-500 mb-4 shadow-xl shadow-rose-950/20" }, Icons.shield("#e11d48", 28)), /* @__PURE__ */ React.createElement("h3", { className: "text-sm font-bold text-slate-200 mb-1" }, "\u0416\u0443\u0440\u043D\u0430\u043B \u0438\u043D\u0446\u0438\u0434\u0435\u043D\u0442\u043E\u0432 \u0447\u0438\u0441\u0442"), /* @__PURE__ */ React.createElement("p", { className: "text-xs text-slate-400 max-w-[260px] leading-relaxed mb-4" }, "\u0412 \u044D\u0442\u043E\u0439 \u0433\u0440\u0443\u043F\u043F\u0435 \u043D\u0430\u0440\u0443\u0448\u0435\u043D\u0438\u0439 \u0435\u0449\u0451 \u043D\u0435 \u0437\u0430\u0444\u0438\u043A\u0441\u0438\u0440\u043E\u0432\u0430\u043D\u043E. \u0418\u0418 \u0438 \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0435 \u0444\u0438\u043B\u044C\u0442\u0440\u044B \u043D\u0435\u043F\u0440\u0435\u0440\u044B\u0432\u043D\u043E \u0432\u0435\u0434\u0443\u0442 \u043C\u043E\u043D\u0438\u0442\u043E\u0440\u0438\u043D\u0433."), /* @__PURE__ */ React.createElement("div", { className: "inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-mono-code font-semibold" }, /* @__PURE__ */ React.createElement("span", { className: "w-2 h-2 rounded-full bg-emerald-500 animate-pulse" }), "\u0417\u0430\u0449\u0438\u0442\u0430 24/7 \u0410\u043A\u0442\u0438\u0432\u043D\u0430"));
    }
    return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-3 pb-24 anim-fade" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center px-1" }, /* @__PURE__ */ React.createElement("span", { className: "text-[11px] font-bold text-slate-400 uppercase tracking-wider" }, "\u041F\u043E\u0441\u043B\u0435\u0434\u043D\u0438\u0435 \u0441\u043E\u0431\u044B\u0442\u0438\u044F"), /* @__PURE__ */ React.createElement("button", { onClick: loadLogs, className: "text-slate-500 hover:text-slate-300 p-1" }, Icons.refresh("#64748b", 14))), logs.map((log) => /* @__PURE__ */ React.createElement("div", { key: log.id, className: "glass-card p-3.5 space-y-2 border-l-4 border-l-rose-500" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-start" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-2" }, /* @__PURE__ */ React.createElement("span", { className: `text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border ${CAT_BADGES[log.category] || "bg-slate-800 text-slate-300"}` }, log.category), log.user_id && /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-[11px] text-slate-400" }, "ID: ", log.user_id)), /* @__PURE__ */ React.createElement("span", { className: "text-[10px] text-slate-500 flex items-center gap-1 font-mono-code" }, Icons.clock("#64748b", 12), " ", formatTimeAgo(log.created_at))), log.reason && /* @__PURE__ */ React.createElement("p", { className: "text-xs text-slate-300 bg-[#07090e]/60 p-2.5 rounded-xl border border-[#1a2233] leading-relaxed" }, log.reason), /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center text-[11px] pt-1" }, /* @__PURE__ */ React.createElement("span", { className: "font-bold text-rose-400" }, ACTION_LABELS[log.action_type] || log.action_type), log.confidence != null && /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-slate-400" }, "\u0423\u0432\u0435\u0440\u0435\u043D\u043D\u043E\u0441\u0442\u044C: ", /* @__PURE__ */ React.createElement("strong", { className: "text-slate-200" }, log.confidence.toFixed(1), "%"))))));
  }
  function TabScanner() {
    const [input, setInput] = useState("");
    const [result, setResult] = useState(null);
    const [scanning, setScanning] = useState(false);
    const [error, setError] = useState(null);
    const runScan = async () => {
      if (!input.trim()) return;
      setScanning(true);
      setError(null);
      setResult(null);
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred("medium");
      try {
        const res = await Api.scanText(input);
        setResult(res);
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred(res.is_violation ? "warning" : "success");
      } catch (err) {
        setError(err.message);
      } finally {
        setScanning(false);
      }
    };
    const setPreset = (text) => {
      setInput(text);
      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
    };
    return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-4 pb-24 anim-fade" }, /* @__PURE__ */ React.createElement("div", { className: "glass-card p-4 space-y-3" }, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-slate-200 uppercase tracking-wider" }, "\u0418\u043D\u0442\u0435\u0440\u0430\u043A\u0442\u0438\u0432\u043D\u044B\u0439 \u0418\u0418-\u0421\u043A\u0430\u043D\u0435\u0440"), /* @__PURE__ */ React.createElement("p", { className: "text-xs text-slate-400 leading-relaxed" }, "\u0412\u0441\u0442\u0430\u0432\u044C\u0442\u0435 \u043B\u044E\u0431\u043E\u0439 \u043F\u043E\u0434\u043E\u0437\u0440\u0438\u0442\u0435\u043B\u044C\u043D\u044B\u0439 \u0442\u0435\u043A\u0441\u0442 \u0434\u043B\u044F \u043C\u0433\u043D\u043E\u0432\u0435\u043D\u043D\u043E\u0439 \u043F\u0440\u043E\u0432\u0435\u0440\u043A\u0438 \u043D\u0435\u0439\u0440\u043E\u0441\u0435\u0442\u044C\u044E NVIDIA NIM Llama 3.1:"), /* @__PURE__ */ React.createElement(
      "textarea",
      {
        rows: "3",
        value: input,
        onChange: (e) => setInput(e.target.value),
        placeholder: "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0442\u0435\u043A\u0441\u0442 \u0434\u043B\u044F \u043F\u0440\u043E\u0432\u0435\u0440\u043A\u0438...",
        className: "w-full bg-[#07090e] border border-[#1a2233] rounded-xl p-3 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-rose-500 resize-none transition-colors"
      }
    ), /* @__PURE__ */ React.createElement("div", { className: "flex flex-wrap gap-1.5 pt-1" }, /* @__PURE__ */ React.createElement("span", { className: "text-[10px] text-slate-500 self-center mr-1" }, "\u041F\u0440\u0438\u043C\u0435\u0440\u044B:"), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setPreset("\u0421\u0440\u043E\u0447\u043D\u043E \u0440\u0430\u0437\u0434\u0430\u0435\u043C 500 TON! \u041F\u0435\u0440\u0435\u0445\u043E\u0434\u0438 \u0432 \u0431\u043E\u0442\u0430 @free_airdrop..."),
        className: "text-[10px] font-medium bg-[#141a27] hover:bg-[#1a2233] text-slate-300 px-2.5 py-1 rounded-lg border border-[#1e2738]"
      },
      "\u041A\u0440\u0438\u043F\u0442\u043E-\u0441\u043A\u0430\u043C"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setPreset("\u0412\u0441\u0435\u043C \u043F\u0440\u0438\u0432\u0435\u0442, \u043A\u043E\u0433\u0434\u0430 \u0441\u043B\u0435\u0434\u0443\u044E\u0449\u0438\u0439 \u0441\u043E\u0437\u0432\u043E\u043D \u043F\u043E \u043F\u0440\u043E\u0435\u043A\u0442\u0443?"),
        className: "text-[10px] font-medium bg-[#141a27] hover:bg-[#1a2233] text-slate-300 px-2.5 py-1 rounded-lg border border-[#1e2738]"
      },
      "\u0427\u0438\u0441\u0442\u044B\u0439 \u0442\u0435\u043A\u0441\u0442"
    )), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: runScan,
        disabled: scanning || !input.trim(),
        className: "w-full mt-2 py-3 bg-[#e11d48] hover:bg-[#be123c] disabled:opacity-40 text-white text-xs font-bold uppercase tracking-wider rounded-xl transition-all active:scale-[0.98]"
      },
      scanning ? "\u0410\u043D\u0430\u043B\u0438\u0437 \u043D\u0435\u0439\u0440\u043E\u0441\u0435\u0442\u044C\u044E..." : "\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0435"
    )), error && /* @__PURE__ */ React.createElement("div", { className: "p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-400" }, error), result && /* @__PURE__ */ React.createElement("div", { className: `glass-card p-4 space-y-2.5 border-l-4 anim-fade ${!result.is_violation ? "border-l-emerald-500 bg-emerald-950/10" : result.confidence < 85 ? "border-l-amber-500 bg-amber-950/10" : "border-l-rose-500 bg-rose-950/10"}` }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-2" }, !result.is_violation ? Icons.check("#10b981", 16) : result.confidence < 85 ? Icons.alert("#f59e0b", 16) : Icons.alert("#e11d48", 16), /* @__PURE__ */ React.createElement("span", { className: `text-xs font-bold uppercase tracking-wider ${!result.is_violation ? "text-emerald-400" : result.confidence < 85 ? "text-amber-400" : "text-rose-400"}` }, !result.is_violation ? "\u0421\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0435 \u0447\u0438\u0441\u0442\u043E\u0435 (\u0411\u0435\u0437\u043E\u043F\u0430\u0441\u043D\u043E)" : result.confidence < 85 ? "\u041D\u0430 \u0440\u0430\u0441\u0441\u043C\u043E\u0442\u0440\u0435\u043D\u0438\u0438 (\u041F\u043E\u0434\u043E\u0437\u0440\u0435\u043D\u0438\u0435)" : "\u041A\u0440\u0438\u0442\u0438\u0447\u0435\u0441\u043A\u0430\u044F \u0443\u0433\u0440\u043E\u0437\u0430 (\u0411\u0410\u041D)")), /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-1.5 font-mono-code text-xs font-bold" }, /* @__PURE__ */ React.createElement("span", { className: "text-[10px] text-slate-400" }, "\u0420\u0438\u0441\u043A:"), /* @__PURE__ */ React.createElement("span", { className: `px-2 py-0.5 rounded-lg border ${!result.is_violation ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" : result.confidence < 85 ? "bg-amber-500/15 text-amber-300 border-amber-500/30" : "bg-rose-500/15 text-rose-400 border-rose-500/30"}` }, result.confidence?.toFixed(1), "%"))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between text-xs pt-1" }, /* @__PURE__ */ React.createElement("span", { className: "text-slate-400" }, "\u041A\u0430\u0442\u0435\u0433\u043E\u0440\u0438\u044F:"), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code font-bold text-slate-200 bg-[#07090e] px-2 py-0.5 rounded border border-[#1a2233]" }, result.category)), /* @__PURE__ */ React.createElement("p", { className: "text-xs text-slate-300 leading-relaxed bg-[#07090e]/60 p-3 rounded-xl border border-[#1a2233]" }, result.reason)));
  }
  function TabDatabase() {
    const [tables, setTables] = useState([]);
    const [selectedTable, setSelectedTable] = useState("chats");
    const [records, setRecords] = useState([]);
    const [totalCount, setTotalCount] = useState(0);
    const [page, setPage] = useState(0);
    const [searchQuery, setSearchQuery] = useState("");
    const [viewMode, setViewMode] = useState("table");
    const [loadingTables, setLoadingTables] = useState(true);
    const [loadingRecords, setLoadingRecords] = useState(false);
    const [error, setError] = useState(null);
    const [selectedRow, setSelectedRow] = useState(null);
    const limit = 20;
    const loadTables = useCallback(() => {
      setLoadingTables(true);
      setError(null);
      Api.getDbTables().then((data) => {
        setTables(data);
        if (data.length > 0 && !data.some((t) => t.id === selectedTable)) {
          setSelectedTable(data[0].id);
        }
      }).catch((err) => setError(err.message)).finally(() => setLoadingTables(false));
    }, [selectedTable]);
    useEffect(() => {
      loadTables();
    }, []);
    const loadRecords = useCallback(() => {
      if (!selectedTable) return;
      setLoadingRecords(true);
      Api.getDbRecords(selectedTable, limit, page * limit, searchQuery).then((res) => {
        setRecords(res.records || []);
        setTotalCount(res.total || 0);
      }).catch((err) => setError(err.message)).finally(() => setLoadingRecords(false));
    }, [selectedTable, page, searchQuery]);
    useEffect(() => {
      loadRecords();
    }, [loadRecords]);
    const currentTableInfo = tables.find((t) => t.id === selectedTable);
    const totalPages = Math.max(1, Math.ceil(totalCount / limit));
    const renderBadge = (key, val) => {
      if (key === "warn_punishment" || key === "action_type") {
        const v = String(val).toLowerCase();
        if (v === "ban" || v === "ban_user") {
          return /* @__PURE__ */ React.createElement("span", { className: "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-500/15 text-rose-400 border border-rose-500/30 shadow-sm shadow-rose-950/40" }, /* @__PURE__ */ React.createElement("span", { className: "w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" }), " \u0411\u0410\u041D");
        }
        if (v === "warn") {
          return /* @__PURE__ */ React.createElement("span", { className: "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30" }, /* @__PURE__ */ React.createElement("span", { className: "w-1.5 h-1.5 rounded-full bg-amber-400" }), " \u0412\u0410\u0420\u041D");
        }
        if (v === "mute" || v === "mute_user") {
          return /* @__PURE__ */ React.createElement("span", { className: "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-500/15 text-indigo-300 border border-indigo-500/30" }, /* @__PURE__ */ React.createElement("span", { className: "w-1.5 h-1.5 rounded-full bg-indigo-400" }), " \u041C\u0423\u0422");
        }
        if (v === "kick") {
          return /* @__PURE__ */ React.createElement("span", { className: "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-orange-500/15 text-orange-300 border border-orange-500/30" }, /* @__PURE__ */ React.createElement("span", { className: "w-1.5 h-1.5 rounded-full bg-orange-400" }), " \u041A\u0418\u041A");
        }
      }
      if (typeof val === "boolean") {
        return /* @__PURE__ */ React.createElement("span", { className: `inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold font-mono ${val ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" : "bg-slate-800 text-slate-500 border border-slate-700/40"}` }, val ? "\u0412\u041A\u041B" : "\u0412\u042B\u041A\u041B");
      }
      if (typeof val === "number") {
        if (key === "trust_score") {
          const pct = Math.round(val * 100);
          return /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-1.5" }, /* @__PURE__ */ React.createElement("div", { className: "w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden" }, /* @__PURE__ */ React.createElement("div", { style: { width: `${pct}%` }, className: `h-full ${pct > 70 ? "bg-emerald-400" : pct > 40 ? "bg-amber-400" : "bg-rose-400"}` })), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-[10px] font-bold text-slate-300" }, pct, "%"));
        }
        if (key.includes("threshold") || key.includes("confidence")) {
          return /* @__PURE__ */ React.createElement("span", { className: "font-mono-code font-bold text-[11px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20" }, Math.round(val), "%");
        }
        return /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-slate-200 text-xs" }, val);
      }
      if (val === null || val === void 0) {
        return /* @__PURE__ */ React.createElement("span", { className: "text-slate-600 font-mono text-[10px] italic" }, "null");
      }
      if (typeof val === "object") {
        return /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-indigo-300 text-[10px] bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20" }, Array.isArray(val) ? `\u041C\u0430\u0441\u0441\u0438\u0432 (${val.length})` : "\u041E\u0431\u044A\u0435\u043A\u0442");
      }
      const strVal = String(val);
      if (strVal.includes("T") && strVal.includes(":") && strVal.length >= 19) {
        const d = new Date(strVal);
        return /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-slate-400 text-[10px]" }, d.toLocaleDateString("ru-RU"), " ", /* @__PURE__ */ React.createElement("span", { className: "text-slate-500" }, d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })));
      }
      if (key === "chat_id" || key === "telegram_id" || key === "admin_telegram_id") {
        return /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-slate-300 text-[11px] select-all" }, strVal);
      }
      return /* @__PURE__ */ React.createElement("span", { className: "text-slate-200 text-xs truncate max-w-[160px] inline-block font-medium" }, strVal);
    };
    if (loadingTables) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-3" }, /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-12" }), /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-32" }), /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-64" }));
    }
    if (error) {
      return /* @__PURE__ */ React.createElement("div", { className: "p-8 text-center flex flex-col items-center justify-center" }, /* @__PURE__ */ React.createElement("div", { className: "w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500 mb-3" }, Icons.alert("#e11d48", 22)), /* @__PURE__ */ React.createElement("p", { className: "text-sm font-bold text-slate-200 mb-1" }, "\u041E\u0448\u0438\u0431\u043A\u0430 \u0431\u0430\u0437\u044B \u0434\u0430\u043D\u043D\u044B\u0445"), /* @__PURE__ */ React.createElement("p", { className: "text-xs text-slate-400 mb-4" }, error), /* @__PURE__ */ React.createElement("button", { onClick: loadTables, className: "px-4 py-2 bg-slate-800 text-xs font-semibold rounded-xl text-slate-200" }, "\u041F\u043E\u0432\u0442\u043E\u0440\u0438\u0442\u044C"));
    }
    return /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-3.5 pb-28 anim-fade" }, /* @__PURE__ */ React.createElement("div", { className: "glass-card p-3.5 flex items-center justify-between border-l-4 border-l-rose-500 shadow-lg" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-3" }, /* @__PURE__ */ React.createElement("div", { className: "w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400" }, Icons.database("#e11d48", 18)), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("h3", { className: "text-xs font-bold text-white uppercase tracking-wider" }, "PostgreSQL Data Explorer"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-400" }, totalCount, " \u0437\u0430\u043F\u0438\u0441\u0435\u0439 \u0432 \u0442\u0430\u0431\u043B\u0438\u0446\u0435 ", /* @__PURE__ */ React.createElement("strong", { className: "text-rose-400 font-mono-code" }, selectedTable)))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-1.5" }, /* @__PURE__ */ React.createElement("div", { className: "flex bg-[#07090e] p-0.5 rounded-xl border border-[#1a2233]" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setViewMode("table"),
        className: `px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${viewMode === "table" ? "bg-[#e11d48] text-white shadow" : "text-slate-400 hover:text-slate-200"}`
      },
      "\u0422\u0430\u0431\u043B\u0438\u0446\u0430"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setViewMode("cards"),
        className: `px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${viewMode === "cards" ? "bg-[#e11d48] text-white shadow" : "text-slate-400 hover:text-slate-200"}`
      },
      "\u041A\u0430\u0440\u0442\u043E\u0447\u043A\u0438"
    )), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          loadTables();
          loadRecords();
          window.Telegram?.WebApp?.HapticFeedback?.impactOccurred("light");
        },
        className: "p-2 rounded-xl bg-[#07090e] border border-[#1a2233] text-slate-400 hover:text-white"
      },
      Icons.refresh("currentColor", 14)
    ))), /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "scroll-touch-x flex items-center gap-2.5 overflow-x-auto no-scrollbar py-1 select-none active:cursor-grabbing cursor-grab",
        onMouseDown: (e) => {
          const el = e.currentTarget;
          el.isDown = true;
          el.startX = e.pageX - el.offsetLeft;
          el.scrollLeftStart = el.scrollLeft;
        },
        onMouseLeave: (e) => {
          e.currentTarget.isDown = false;
        },
        onMouseUp: (e) => {
          e.currentTarget.isDown = false;
        },
        onMouseMove: (e) => {
          const el = e.currentTarget;
          if (!el.isDown) return;
          e.preventDefault();
          const x = e.pageX - el.offsetLeft;
          const walk = (x - el.startX) * 1.5;
          el.scrollLeft = el.scrollLeftStart - walk;
        }
      },
      tables.map((tbl) => {
        const active = tbl.id === selectedTable;
        return /* @__PURE__ */ React.createElement(
          "button",
          {
            key: tbl.id,
            onClick: () => {
              setSelectedTable(tbl.id);
              setPage(0);
              setSearchQuery("");
              window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
            },
            className: `shrink-0 min-w-[150px] flex items-center gap-2.5 px-4 py-3 rounded-2xl border transition-all ${active ? "bg-gradient-to-r from-rose-950/70 to-[#0d111a] border-rose-500 shadow-lg shadow-rose-950/40 scale-[1.02]" : "bg-[#0d111a] text-slate-400 border-[#1a2233] hover:text-slate-200 hover:border-slate-700"}`
          },
          /* @__PURE__ */ React.createElement("div", { className: `w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${active ? "bg-rose-500 text-white" : "bg-slate-800 text-slate-400"}` }, Icons.table("currentColor", 15)),
          /* @__PURE__ */ React.createElement("div", { className: "text-left" }, /* @__PURE__ */ React.createElement("p", { className: `text-xs font-bold leading-tight ${active ? "text-white" : "text-slate-300"}` }, tbl.title), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] font-mono-code text-slate-500 mt-0.5" }, tbl.total_rows, " \u0437\u0430\u043F\u0438\u0441\u0435\u0439"))
        );
      })
    ), /* @__PURE__ */ React.createElement("div", { className: "relative" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "text",
        value: searchQuery,
        onChange: (e) => {
          setSearchQuery(e.target.value);
          setPage(0);
        },
        placeholder: `\u041F\u043E\u0438\u0441\u043A \u0432 ${currentTableInfo?.title || "\u0442\u0430\u0431\u043B\u0438\u0446\u0435"}...`,
        className: "w-full bg-[#0d111a] border border-[#1a2233] rounded-2xl pl-9 pr-8 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500 transition-colors"
      }
    ), /* @__PURE__ */ React.createElement("div", { className: "absolute left-3 top-3 text-slate-500" }, Icons.search("#64748b", 14)), searchQuery && /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          setSearchQuery("");
          setPage(0);
        },
        className: "absolute right-3 top-2.5 text-slate-500 hover:text-slate-300 font-bold text-xs"
      },
      "\u2715"
    )), loadingRecords ? /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-2" }, [1, 2, 3, 4, 5].map((i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "skeleton-box h-12" }))) : records.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "glass-card p-10 text-center flex flex-col items-center justify-center" }, /* @__PURE__ */ React.createElement("div", { className: "w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-2" }, Icons.table("#64748b", 20)), /* @__PURE__ */ React.createElement("p", { className: "text-xs font-bold text-slate-300" }, "\u0417\u0430\u043F\u0438\u0441\u0435\u0439 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E"), /* @__PURE__ */ React.createElement("p", { className: "text-[11px] text-slate-500 mt-0.5" }, "\u0412 \u0442\u0430\u0431\u043B\u0438\u0446\u0435 ", selectedTable, " \u043F\u043E\u043A\u0430 \u043D\u0435\u0442 \u0434\u0430\u043D\u043D\u044B\u0445 \u0438\u043B\u0438 \u043F\u043E\u0438\u0441\u043A \u043D\u0435 \u0434\u0430\u043B \u0440\u0435\u0437\u0443\u043B\u044C\u0442\u0430\u0442\u043E\u0432")) : viewMode === "cards" ? (
      /* Card Deck View */
      /* @__PURE__ */ React.createElement("div", { className: "space-y-3" }, records.map((row, idx) => /* @__PURE__ */ React.createElement(
        "div",
        {
          key: idx,
          onClick: () => setSelectedRow(row),
          className: "glass-card p-4 space-y-2.5 border border-[#1a2233] hover:border-rose-500/40 transition-all cursor-pointer relative overflow-hidden"
        },
        /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-start" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-2" }, /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-xs font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-lg border border-rose-500/20" }, "#", row.id || row.chat_id || idx + 1), row.title && /* @__PURE__ */ React.createElement("span", { className: "text-xs font-bold text-white truncate max-w-[180px]" }, row.title), row.username && /* @__PURE__ */ React.createElement("span", { className: "text-xs text-slate-300 font-mono-code" }, "@", row.username)), row.warn_punishment && renderBadge("warn_punishment", row.warn_punishment), row.action_type && renderBadge("action_type", row.action_type), row.is_active !== void 0 && renderBadge("is_active", row.is_active)),
        /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-2 gap-2 pt-1 text-xs" }, currentTableInfo?.columns.filter((c) => !["id", "chat_id", "title", "username"].includes(c.key)).slice(0, 6).map((col) => /* @__PURE__ */ React.createElement("div", { key: col.key, className: "bg-[#07090e]/60 p-2 rounded-xl border border-[#1a2233]/60 flex flex-col justify-between" }, /* @__PURE__ */ React.createElement("span", { className: "text-[10px] text-slate-400 uppercase font-semibold" }, col.label), /* @__PURE__ */ React.createElement("div", { className: "mt-1" }, renderBadge(col.key, row[col.key]))))),
        /* @__PURE__ */ React.createElement("div", { className: "flex justify-between items-center pt-1 border-t border-[#1a2233]" }, /* @__PURE__ */ React.createElement("span", { className: "text-[10px] text-slate-400 font-mono-code" }, row.created_at ? new Date(row.created_at).toLocaleString("ru-RU") : ""), /* @__PURE__ */ React.createElement(
          "button",
          {
            onClick: (e) => {
              e.stopPropagation();
              setSelectedRow(row);
            },
            className: "text-[10px] font-bold text-rose-400 hover:text-rose-300 uppercase tracking-wider flex items-center gap-1"
          },
          "\u041F\u043E\u0434\u0440\u043E\u0431\u043D\u0435\u0435 JSON \u2192"
        ))
      )))
    ) : (
      /* Horizontal Scrollable Table View with Centered Sanction Badges */
      /* @__PURE__ */ React.createElement("div", { className: "glass-card overflow-hidden border border-[#1a2233] relative" }, /* @__PURE__ */ React.createElement("div", { className: "overflow-x-auto no-scrollbar" }, /* @__PURE__ */ React.createElement("table", { className: "w-full text-left text-xs border-collapse" }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { className: "bg-[#07090e] border-b border-[#1a2233]" }, currentTableInfo?.columns.map((col) => /* @__PURE__ */ React.createElement("th", { key: col.key, className: "px-4 py-3 text-[10px] uppercase font-bold text-slate-400 tracking-wider whitespace-nowrap" }, col.label)), /* @__PURE__ */ React.createElement("th", { className: "px-4 py-3 text-[10px] uppercase font-bold text-slate-400 tracking-wider text-right whitespace-nowrap" }, "JSON"))), /* @__PURE__ */ React.createElement("tbody", { className: "divide-y divide-[#1a2233]" }, records.map((row, rowIdx) => /* @__PURE__ */ React.createElement(
        "tr",
        {
          key: rowIdx,
          onClick: () => setSelectedRow(row),
          className: "hover:bg-rose-950/10 transition-colors cursor-pointer"
        },
        currentTableInfo?.columns.map((col) => /* @__PURE__ */ React.createElement("td", { key: col.key, className: "px-4 py-3 whitespace-nowrap" }, renderBadge(col.key, row[col.key]))),
        /* @__PURE__ */ React.createElement("td", { className: "px-4 py-3 text-right whitespace-nowrap" }, /* @__PURE__ */ React.createElement(
          "button",
          {
            onClick: (e) => {
              e.stopPropagation();
              setSelectedRow(row);
            },
            className: "px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono-code text-[10px]"
          },
          "JSON"
        ))
      ))))))
    ), totalPages > 1 && /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between px-1 pt-1 text-xs" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          setPage((p) => Math.max(0, p - 1));
          window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
        },
        disabled: page <= 0,
        className: "px-3.5 py-2 rounded-xl bg-[#0d111a] border border-[#1a2233] text-slate-300 disabled:opacity-30 disabled:pointer-events-none font-semibold text-xs transition-all active:scale-95"
      },
      "\u2190 \u041D\u0430\u0437\u0430\u0434"
    ), /* @__PURE__ */ React.createElement("span", { className: "font-mono-code text-[11px] text-slate-400" }, "\u0421\u0442\u0440. ", /* @__PURE__ */ React.createElement("strong", { className: "text-white" }, page + 1), " \u0438\u0437 ", totalPages, " (", totalCount, " \u0437\u0430\u043F\u0438\u0441\u0435\u0439)"), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          setPage((p) => Math.min(totalPages - 1, p + 1));
          window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
        },
        disabled: page >= totalPages - 1,
        className: "px-3.5 py-2 rounded-xl bg-[#0d111a] border border-[#1a2233] text-slate-300 disabled:opacity-30 disabled:pointer-events-none font-semibold text-xs transition-all active:scale-95"
      },
      "\u0412\u043F\u0435\u0440\u0451\u0434 \u2192"
    )), selectedRow && /* @__PURE__ */ React.createElement("div", { className: "fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 anim-fade" }, /* @__PURE__ */ React.createElement("div", { className: "glass-card max-w-md w-full max-h-[85vh] flex flex-col overflow-hidden border border-rose-500/40 shadow-2xl" }, /* @__PURE__ */ React.createElement("div", { className: "p-4 bg-[#07090e] border-b border-[#1a2233] flex justify-between items-center" }, /* @__PURE__ */ React.createElement("h4", { className: "text-xs font-bold text-white uppercase tracking-wider font-mono-code flex items-center gap-2" }, Icons.table("#e11d48", 16), " ", selectedTable, " // \u0417\u0430\u043F\u0438\u0441\u044C"), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setSelectedRow(null),
        className: "w-7 h-7 rounded-xl bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center font-bold text-xs"
      },
      "\u2715"
    )), /* @__PURE__ */ React.createElement("div", { className: "p-4 overflow-y-auto no-scrollbar font-mono-code text-[11px] text-slate-300 bg-[#080b11] space-y-2" }, /* @__PURE__ */ React.createElement("pre", { className: "whitespace-pre-wrap break-all leading-relaxed text-emerald-400 selection:bg-rose-500/30" }, JSON.stringify(selectedRow, null, 2))), /* @__PURE__ */ React.createElement("div", { className: "p-3.5 bg-[#07090e] border-t border-[#1a2233] flex justify-end" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setSelectedRow(null),
        className: "px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold rounded-xl"
      },
      "\u0417\u0430\u043A\u0440\u044B\u0442\u044C"
    )))));
  }
  function App() {
    const [activeTab, setActiveTab] = useState("overview");
    const [user, setUser] = useState(null);
    const [chats, setChats] = useState(null);
    const [selectedChatId, setSelectedChatId] = useState(null);
    const [loadingChats, setLoadingChats] = useState(true);
    const [chatError, setChatError] = useState(null);
    useEffect(() => {
      const tg = getTelegramWebApp();
      if (tg?.initDataUnsafe?.user) {
        setUser(tg.initDataUnsafe.user);
      }
      const urlParams = new URLSearchParams(window.location.search);
      const queryChatId = urlParams.get("chat_id");
      Api.getChats().then((chatList) => {
        setChats(chatList);
        if (chatList.length > 0) {
          if (queryChatId && chatList.some((c) => String(c.chat_id) === queryChatId)) {
            setSelectedChatId(Number(queryChatId));
          } else {
            setSelectedChatId(chatList[0].chat_id);
          }
        }
      }).catch((err) => setChatError(err.message)).finally(() => setLoadingChats(false));
    }, []);
    const currentChat = chats?.find((c) => c.chat_id === selectedChatId);
    const TABS = [
      { id: "overview", icon: Icons.chart, label: "\u041E\u0431\u0437\u043E\u0440" },
      { id: "settings", icon: Icons.tune, label: "\u0424\u0438\u043B\u044C\u0442\u0440\u044B" },
      { id: "logs", icon: Icons.list, label: "\u0416\u0443\u0440\u043D\u0430\u043B" },
      { id: "database", icon: Icons.database, label: "\u0411\u0430\u0437\u0430 \u0414\u0430\u043D\u043D\u044B\u0445" },
      { id: "scanner", icon: Icons.search, label: "\u0421\u043A\u0430\u043D\u0435\u0440" }
    ];
    return /* @__PURE__ */ React.createElement("div", { className: "max-w-lg mx-auto min-h-screen flex flex-col bg-[#07090e] text-slate-100" }, /* @__PURE__ */ React.createElement("header", { className: "glass-header sticky top-0 z-50 px-4 pt-3.5 pb-3 space-y-3" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center justify-between" }, /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-2.5" }, /* @__PURE__ */ React.createElement("div", { className: "w-8 h-8 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500 pulse-glow" }, Icons.shield("#e11d48", 18)), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("h1", { className: "text-sm font-bold tracking-tight text-white leading-tight" }, user ? `${user.first_name}` : "TelegramWarden"), /* @__PURE__ */ React.createElement("p", { className: "text-[10px] font-mono-code text-slate-400 leading-tight" }, "NVIDIA NIM \u2022 Llama 3.1"))), /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20" }, /* @__PURE__ */ React.createElement("span", { className: "w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" }), /* @__PURE__ */ React.createElement("span", { className: "text-[10px] font-mono-code font-bold text-emerald-400 uppercase" }, "ONLINE"))), !loadingChats && chats && chats.length > 0 && activeTab !== "database" && /* @__PURE__ */ React.createElement("div", { className: "flex items-center gap-1.5 overflow-x-auto no-scrollbar pt-1" }, chats.map((c) => {
      const active = c.chat_id === selectedChatId;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: c.chat_id,
          onClick: () => {
            setSelectedChatId(c.chat_id);
            window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
          },
          className: `shrink-0 text-xs font-semibold px-3 py-1.5 rounded-xl border transition-all ${active ? "bg-[#e11d48] text-white border-rose-500 shadow-md shadow-rose-950/60" : "bg-[#0d111a] text-slate-400 border-[#1a2233] hover:text-slate-200"}`
        },
        c.title
      );
    }))), /* @__PURE__ */ React.createElement("main", { className: "flex-1 overflow-y-auto no-scrollbar" }, activeTab === "database" ? /* @__PURE__ */ React.createElement(TabDatabase, null) : loadingChats ? /* @__PURE__ */ React.createElement("div", { className: "p-4 space-y-3" }, /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-10" }), /* @__PURE__ */ React.createElement("div", { className: "grid grid-cols-2 gap-3" }, [1, 2, 3, 4].map((i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "skeleton-box h-24" }))), /* @__PURE__ */ React.createElement("div", { className: "skeleton-box h-44" })) : chatError ? /* @__PURE__ */ React.createElement("div", { className: "p-8 text-center flex flex-col items-center justify-center" }, /* @__PURE__ */ React.createElement("p", { className: "text-xs text-rose-400 mb-3" }, chatError), /* @__PURE__ */ React.createElement("button", { onClick: () => window.location.reload(), className: "px-4 py-2 bg-slate-800 text-xs font-semibold rounded-xl" }, "\u041E\u0431\u043D\u043E\u0432\u0438\u0442\u044C")) : !chats || chats.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "p-8 text-center flex flex-col items-center justify-center min-h-[380px]" }, /* @__PURE__ */ React.createElement("div", { className: "w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-3" }, Icons.shield("#64748b", 24)), /* @__PURE__ */ React.createElement("h3", { className: "text-sm font-bold text-slate-200 mb-1" }, "\u041D\u0435\u0442 \u0434\u043E\u0441\u0442\u0443\u043F\u043D\u044B\u0445 \u0433\u0440\u0443\u043F\u043F"), /* @__PURE__ */ React.createElement("p", { className: "text-xs text-slate-400 max-w-[280px] leading-relaxed" }, "\u0414\u043E\u0431\u0430\u0432\u044C\u0442\u0435 \u0431\u043E\u0442\u0430 \u0432 \u0433\u0440\u0443\u043F\u043F\u0443 \u0438 \u043D\u0430\u0437\u043D\u0430\u0447\u044C\u0442\u0435 \u0430\u0434\u043C\u0438\u043D\u0438\u0441\u0442\u0440\u0430\u0442\u043E\u0440\u043E\u043C, \u0438\u043B\u0438 \u043F\u043E\u043F\u0440\u043E\u0441\u0438\u0442\u0435 \u0432\u043B\u0430\u0434\u0435\u043B\u044C\u0446\u0430 \u0434\u043E\u0431\u0430\u0432\u0438\u0442\u044C \u0432\u0430\u0448 ID \u0432 \u0431\u0435\u043B\u044B\u0439 \u0441\u043F\u0438\u0441\u043E\u043A.")) : selectedChatId ? /* @__PURE__ */ React.createElement(React.Fragment, null, activeTab === "overview" && /* @__PURE__ */ React.createElement(TabOverview, { chatId: selectedChatId }), activeTab === "settings" && /* @__PURE__ */ React.createElement(TabSettings, { chatId: selectedChatId }), activeTab === "logs" && /* @__PURE__ */ React.createElement(TabLogs, { chatId: selectedChatId }), activeTab === "scanner" && /* @__PURE__ */ React.createElement(TabScanner, null)) : null), /* @__PURE__ */ React.createElement("nav", { className: "glass-nav fixed bottom-0 left-0 right-0 max-w-lg mx-auto z-50" }, /* @__PURE__ */ React.createElement("div", { className: "flex justify-around items-center h-14 px-2" }, TABS.map((t) => {
      const active = activeTab === t.id;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: t.id,
          onClick: () => {
            setActiveTab(t.id);
            window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
          },
          className: `flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl transition-all ${active ? "text-[#e11d48]" : "text-slate-400 hover:text-slate-200"}`
        },
        t.icon(active ? "#e11d48" : "#94a3b8", 18),
        /* @__PURE__ */ React.createElement("span", { className: `text-[10px] ${active ? "font-bold" : "font-medium"}` }, t.label)
      );
    }))));
  }
  window.ReactDOM.render(/* @__PURE__ */ React.createElement(App, null), document.getElementById("root"));
})();
