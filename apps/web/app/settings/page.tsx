'use client';

import { useState } from 'react';
import { Save, Key, Server, Cpu } from 'lucide-react';

interface Settings {
  openai_api_key: string;
  ollama_base_url: string;
  default_model: string;
  max_cards_per_slide: number;
  auto_dedupe: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    openai_api_key: '',
    ollama_base_url: 'http://localhost:11434',
    default_model: 'openai',
    max_cards_per_slide: 5,
    auto_dedupe: true,
  });
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // TODO: Save to backend
    localStorage.setItem('slide2anki_settings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Settings</h1>

      <div className="bg-white rounded-lg border divide-y">
        {/* Model Configuration */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Model Configuration</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Default Model Backend
              </label>
              <select
                value={settings.default_model}
                onChange={(e) =>
                  setSettings({ ...settings, default_model: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="openai">OpenAI (GPT-4 Vision)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
          </div>
        </div>

        {/* OpenAI Settings */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-5 h-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">OpenAI</h2>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Key
            </label>
            <input
              type="password"
              value={settings.openai_api_key}
              onChange={(e) =>
                setSettings({ ...settings, openai_api_key: e.target.value })
              }
              placeholder="sk-..."
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Your API key is stored locally and never sent to our servers.
            </p>
          </div>
        </div>

        {/* Ollama Settings */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Ollama</h2>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Base URL
            </label>
            <input
              type="text"
              value={settings.ollama_base_url}
              onChange={(e) =>
                setSettings({ ...settings, ollama_base_url: e.target.value })
              }
              placeholder="http://localhost:11434"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>

        {/* Processing Settings */}
        <div className="p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Processing</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Cards per Slide
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={settings.max_cards_per_slide}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    max_cards_per_slide: parseInt(e.target.value) || 5,
                  })
                }
                className="w-32 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="auto_dedupe"
                checked={settings.auto_dedupe}
                onChange={(e) =>
                  setSettings({ ...settings, auto_dedupe: e.target.checked })
                }
                className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
              />
              <label htmlFor="auto_dedupe" className="text-sm text-gray-700">
                Automatically deduplicate similar cards
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-6 flex items-center justify-end gap-4">
        {saved && (
          <span className="text-sm text-green-600">Settings saved!</span>
        )}
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <Save className="w-4 h-4" />
          Save Settings
        </button>
      </div>
    </div>
  );
}
