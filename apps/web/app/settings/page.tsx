'use client';

import { useState } from 'react';
import { Save, Key, Server, Cpu } from 'lucide-react';

/**
 * Model provider configuration with available models for each.
 * Models are organized by provider with metadata for vision capability and cost tier.
 */
interface ModelOption {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic' | 'google' | 'ollama';
  hasVision: boolean;
  tier: 'flagship' | 'standard' | 'efficient';
  description: string;
}

const AVAILABLE_MODELS: ModelOption[] = [
  // OpenAI Models
  {
    id: 'gpt-4.1',
    name: 'GPT-4.1',
    provider: 'openai',
    hasVision: true,
    tier: 'flagship',
    description: 'Latest flagship model with enhanced reasoning',
  },
  {
    id: 'gpt-4.1-mini',
    name: 'GPT-4.1 Mini',
    provider: 'openai',
    hasVision: true,
    tier: 'efficient',
    description: 'Fast and cost-effective for simple tasks',
  },
  {
    id: 'gpt-4.1-nano',
    name: 'GPT-4.1 Nano',
    provider: 'openai',
    hasVision: true,
    tier: 'efficient',
    description: 'Ultra-lightweight for quick operations',
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    hasVision: true,
    tier: 'flagship',
    description: 'Multimodal flagship with vision capabilities',
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    hasVision: true,
    tier: 'efficient',
    description: 'Efficient multimodal model',
  },
  {
    id: 'o3',
    name: 'o3',
    provider: 'openai',
    hasVision: true,
    tier: 'flagship',
    description: 'Advanced reasoning model',
  },
  {
    id: 'o3-mini',
    name: 'o3 Mini',
    provider: 'openai',
    hasVision: true,
    tier: 'efficient',
    description: 'Efficient reasoning model',
  },
  {
    id: 'o4-mini',
    name: 'o4 Mini',
    provider: 'openai',
    hasVision: true,
    tier: 'efficient',
    description: 'Latest efficient reasoning model',
  },

  // Anthropic Models
  {
    id: 'claude-opus-4',
    name: 'Claude Opus 4',
    provider: 'anthropic',
    hasVision: true,
    tier: 'flagship',
    description: 'Most capable Claude model for complex tasks',
  },
  {
    id: 'claude-sonnet-4',
    name: 'Claude Sonnet 4',
    provider: 'anthropic',
    hasVision: true,
    tier: 'standard',
    description: 'Balanced performance and speed',
  },
  {
    id: 'claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'anthropic',
    hasVision: true,
    tier: 'standard',
    description: 'Previous generation balanced model',
  },
  {
    id: 'claude-3.5-haiku',
    name: 'Claude 3.5 Haiku',
    provider: 'anthropic',
    hasVision: true,
    tier: 'efficient',
    description: 'Fast and cost-effective',
  },

  // Google Gemini Models
  {
    id: 'gemini-2.5-pro',
    name: 'Gemini 2.5 Pro',
    provider: 'google',
    hasVision: true,
    tier: 'flagship',
    description: 'Latest flagship Gemini with advanced reasoning',
  },
  {
    id: 'gemini-2.5-flash',
    name: 'Gemini 2.5 Flash',
    provider: 'google',
    hasVision: true,
    tier: 'efficient',
    description: 'Fast and efficient Gemini model',
  },
  {
    id: 'gemini-2.0-flash',
    name: 'Gemini 2.0 Flash',
    provider: 'google',
    hasVision: true,
    tier: 'efficient',
    description: 'Previous generation fast model',
  },
  {
    id: 'gemini-2.0-flash-lite',
    name: 'Gemini 2.0 Flash Lite',
    provider: 'google',
    hasVision: true,
    tier: 'efficient',
    description: 'Ultra-lightweight Gemini',
  },

  // Ollama Local Models
  {
    id: 'llava',
    name: 'LLaVA',
    provider: 'ollama',
    hasVision: true,
    tier: 'standard',
    description: 'Local vision model via Ollama',
  },
  {
    id: 'llama3.3',
    name: 'Llama 3.3',
    provider: 'ollama',
    hasVision: false,
    tier: 'standard',
    description: 'Latest Llama for text tasks',
  },
  {
    id: 'llama3.2-vision',
    name: 'Llama 3.2 Vision',
    provider: 'ollama',
    hasVision: true,
    tier: 'standard',
    description: 'Llama with vision capabilities',
  },
  {
    id: 'qwen2.5',
    name: 'Qwen 2.5',
    provider: 'ollama',
    hasVision: false,
    tier: 'standard',
    description: 'High-quality open model',
  },
  {
    id: 'mistral',
    name: 'Mistral',
    provider: 'ollama',
    hasVision: false,
    tier: 'efficient',
    description: 'Fast and capable local model',
  },
];

interface Settings {
  openai_api_key: string;
  anthropic_api_key: string;
  google_api_key: string;
  ollama_base_url: string;
  default_provider: 'openai' | 'anthropic' | 'google' | 'ollama';
  vision_model: string;
  text_model: string;
  max_cards_per_slide: number;
  auto_dedupe: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    openai_api_key: '',
    anthropic_api_key: '',
    google_api_key: '',
    ollama_base_url: 'http://localhost:11434',
    default_provider: 'openai',
    vision_model: 'gpt-4o',
    text_model: 'gpt-4o',
    max_cards_per_slide: 5,
    auto_dedupe: true,
  });
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    localStorage.setItem('slide2anki_settings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const getModelsForProvider = (provider: string) =>
    AVAILABLE_MODELS.filter((m) => m.provider === provider);

  const getVisionModels = () =>
    AVAILABLE_MODELS.filter(
      (m) => m.provider === settings.default_provider && m.hasVision
    );

  const getTextModels = () =>
    AVAILABLE_MODELS.filter((m) => m.provider === settings.default_provider);

  const getTierBadge = (tier: string) => {
    const colors: Record<string, string> = {
      flagship: 'bg-purple-100 text-purple-700',
      standard: 'bg-blue-100 text-blue-700',
      efficient: 'bg-green-100 text-green-700',
    };
    return colors[tier] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Settings</h1>

      <div className="bg-white rounded-lg border divide-y">
        {/* Model Provider Selection */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Model Provider</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Default Provider
              </label>
              <select
                value={settings.default_provider}
                onChange={(e) => {
                  const provider = e.target.value as Settings['default_provider'];
                  const providerModels = getModelsForProvider(provider);
                  const visionModel = providerModels.find((m) => m.hasVision)?.id || providerModels[0]?.id || '';
                  const textModel = providerModels[0]?.id || '';
                  setSettings({
                    ...settings,
                    default_provider: provider,
                    vision_model: visionModel,
                    text_model: textModel,
                  });
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="google">Google (Gemini)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Vision Model
                <span className="ml-2 text-xs text-gray-500">(for slide extraction)</span>
              </label>
              <select
                value={settings.vision_model}
                onChange={(e) =>
                  setSettings({ ...settings, vision_model: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                {getVisionModels().map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} - {model.description}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Text Model
                <span className="ml-2 text-xs text-gray-500">(for card generation)</span>
              </label>
              <select
                value={settings.text_model}
                onChange={(e) =>
                  setSettings({ ...settings, text_model: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                {getTextModels().map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} - {model.description}
                  </option>
                ))}
              </select>
            </div>

            {/* Model Info */}
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600 mb-2">Model Tiers:</p>
              <div className="flex gap-2 flex-wrap">
                <span className={`text-xs px-2 py-1 rounded ${getTierBadge('flagship')}`}>
                  Flagship - Most capable
                </span>
                <span className={`text-xs px-2 py-1 rounded ${getTierBadge('standard')}`}>
                  Standard - Balanced
                </span>
                <span className={`text-xs px-2 py-1 rounded ${getTierBadge('efficient')}`}>
                  Efficient - Fast & cheap
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* API Keys */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-5 h-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">API Keys</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                OpenAI API Key
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
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Anthropic API Key
              </label>
              <input
                type="password"
                value={settings.anthropic_api_key}
                onChange={(e) =>
                  setSettings({ ...settings, anthropic_api_key: e.target.value })
                }
                placeholder="sk-ant-..."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Google AI API Key
              </label>
              <input
                type="password"
                value={settings.google_api_key}
                onChange={(e) =>
                  setSettings({ ...settings, google_api_key: e.target.value })
                }
                placeholder="AIza..."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <p className="text-xs text-gray-500">
              API keys are stored locally and never sent to our servers.
            </p>
          </div>
        </div>

        {/* Ollama Settings */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Ollama (Local)</h2>
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
            <p className="mt-1 text-xs text-gray-500">
              Run models locally without API costs.
            </p>
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
