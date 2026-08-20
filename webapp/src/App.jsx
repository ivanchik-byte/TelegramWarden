import React, { useState, useEffect } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('stats');
  const [chatId, setChatId] = useState(-1001234567890);
  const [loading, setLoading] = useState(false);

  // Settings State
  const [settings, setSettings] = useState({
    title: 'Основная группа',
    is_active: true,
    captcha_enabled: true,
    allow_sender_chat: false,
    clean_service_messages: true,
    ai_moderation_enabled: true,
    ai_confidence_threshold: 85,
    warn_limit: 3,
    night_mode_enabled: false,
  });

  // Statistics State
  const [stats, setStats] = useState({
    total_violations: 42,
    total_bans: 12,
    total_warns_issued: 28,
    total_mutes: 5,
    false_positives_count: 1,
    violations_by_category: [
      { category: 'crypto_scam', count: 18 },
      { category: 'commercial_ad', count: 14 },
      { category: 'adult_nsfw', count: 6 },
      { category: 'toxic_insult', count: 4 },
    ]
  });

  // Audit Logs State
  const [logs, setLogs] = useState([
    {
      id: 101,
      user_id: 987654,
      action_type: 'ban_user',
      category: 'crypto_scam',
      reason: 'Завуалированный призыв перейти в ЛС для раздачи TON',
      confidence: 97.5,
      time: '10 минут назад',
    },
    {
      id: 100,
      user_id: 123456,
      action_type: 'warn',
      category: 'commercial_ad',
      reason: 'Реклама стороннего канала в тексте',
      confidence: 92.0,
      time: '25 минут назад',
    },
    {
      id: 99,
      user_id: 654321,
      action_type: 'delete_message',
      category: 'adult_nsfw',
      reason: 'Обнаружен неприемлемый контент через NudeNet',
      confidence: 98.2,
      time: '1 час назад',
    }
  ]);

  useEffect(() => {
    // Initialize Telegram WebApp
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand();
    }
  }, []);

  const toggleSetting = (key) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }));
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
  };

  const handleSliderChange = (val) => {
    setSettings((prev) => ({ ...prev, ai_confidence_threshold: Number(val) }));
  };

  return (
    <div className="max-w-md mx-auto p-4 pb-20">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">TelegramWarden</h1>
          <p className="text-xs text-slate-400">{settings.title}</p>
        </div>
        <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Защита активна
        </span>
      </header>

      {/* Tabs */}
      <nav className="flex rounded-lg bg-slate-900 p-1 mb-5 border border-slate-800">
        <button
          onClick={() => setActiveTab('stats')}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition ${
            activeTab === 'stats' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
          }`}
        >
          Статистика
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition ${
            activeTab === 'settings' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
          }`}
        >
          Настройки
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition ${
            activeTab === 'logs' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
          }`}
        >
          Журнал
        </button>
      </nav>

      {/* 1. Statistics Tab */}
      {activeTab === 'stats' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
              <p className="text-xs text-slate-400">Всего нарушений</p>
              <p className="text-2xl font-bold text-white mt-1">{stats.total_violations}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
              <p className="text-xs text-slate-400">Заблокировано</p>
              <p className="text-2xl font-bold text-red-400 mt-1">{stats.total_bans}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
              <p className="text-xs text-slate-400">Предупреждений</p>
              <p className="text-2xl font-bold text-amber-400 mt-1">{stats.total_warns_issued}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
              <p className="text-xs text-slate-400">Точность ИИ</p>
              <p className="text-2xl font-bold text-emerald-400 mt-1">98.8%</p>
            </div>
          </div>

          {/* Breakdown by Category */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Нарушения по категориям</h3>
            <div className="space-y-2.5">
              {stats.violations_by_category.map((item) => (
                <div key={item.category} className="flex items-center justify-between text-xs">
                  <span className="text-slate-300 capitalize">{item.category.replace('_', ' ')}</span>
                  <span className="font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-200">
                    {item.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 2. Settings Tab */}
      {activeTab === 'settings' && (
        <div className="space-y-3">
          {/* AI Confidence Slider */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-white">Порог уверенности ИИ</span>
              <span className="text-xs font-bold text-blue-400">{settings.ai_confidence_threshold}%</span>
            </div>
            <input
              type="range"
              min="50"
              max="98"
              value={settings.ai_confidence_threshold}
              onChange={(e) => handleSliderChange(e.target.value)}
              className="w-full accent-blue-500"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Действия применяются автоматически, если уверенность ИИ выше порога.
            </p>
          </div>

          {/* Toggle Switches */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl divide-y divide-slate-800">
            <div className="flex items-center justify-between p-3.5">
              <div>
                <p className="text-sm font-medium text-white">Капча при входе</p>
                <p className="text-xs text-slate-400">Кнопка «Я человек» для новичков</p>
              </div>
              <input
                type="checkbox"
                checked={settings.captcha_enabled}
                onChange={() => toggleSetting('captcha_enabled')}
                className="w-5 h-5 accent-blue-600 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-3.5">
              <div>
                <p className="text-sm font-medium text-white">Запрет сторонних каналов</p>
                <p className="text-xs text-slate-400">Блокировать отправку от имени каналов</p>
              </div>
              <input
                type="checkbox"
                checked={!settings.allow_sender_chat}
                onChange={() => toggleSetting('allow_sender_chat')}
                className="w-5 h-5 accent-blue-600 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-3.5">
              <div>
                <p className="text-sm font-medium text-white">Очистка системных сообщений</p>
                <p className="text-xs text-slate-400">Удалять плашки о входе и выходе</p>
              </div>
              <input
                type="checkbox"
                checked={settings.clean_service_messages}
                onChange={() => toggleSetting('clean_service_messages')}
                className="w-5 h-5 accent-blue-600 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-3.5">
              <div>
                <p className="text-sm font-medium text-white">ИИ Intent-фильтрация</p>
                <p className="text-xs text-slate-400">Семантический анализ DeepSeek / Groq</p>
              </div>
              <input
                type="checkbox"
                checked={settings.ai_moderation_enabled}
                onChange={() => toggleSetting('ai_moderation_enabled')}
                className="w-5 h-5 accent-blue-600 rounded"
              />
            </div>
          </div>
        </div>
      )}

      {/* 3. Audit Logs Tab */}
      {activeTab === 'logs' && (
        <div className="space-y-2.5">
          {logs.map((log) => (
            <div key={log.id} className="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-200">ID: {log.user_id}</span>
                <span className="text-slate-400 text-[11px]">{log.time}</span>
              </div>
              <p className="text-xs text-slate-300">{log.reason}</p>
              <div className="flex justify-between items-center pt-1 border-t border-slate-800/60 text-[11px]">
                <span className="text-blue-400 font-medium capitalize">{log.action_type.replace('_', ' ')}</span>
                <span className="text-slate-400">Уверенность: {log.confidence}%</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
