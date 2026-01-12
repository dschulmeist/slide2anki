'use client';

import { useEffect, useState } from 'react';
import { Save, Key, Server, Cpu, Wifi } from 'lucide-react';

import { api, AppSettings } from '@/lib/api';

/**
 * Model provider configuration with available models for each.
 * Models are organized by provider with metadata for vision capability and cost tier.
 */
interface ModelOption {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic' | 'google' | 'mistral' | 'openrouter' | 'ollama';
  hasVision: boolean;
  tier: 'flagship' | 'standard' | 'efficient';
  description: string;
  inputCost?: string;
  outputCost?: string;
  contextTokens?: number;
}

interface ModelMetadataEntry {
  id: string;
  name?: string;
  contextTokens?: number;
  inputCost?: string;
  outputCost?: string;
  note?: string;
}

type PingStatus = 'idle' | 'loading' | 'success' | 'error';

const AVAILABLE_MODELS: ModelOption[] = [
  // OpenAI Models
  {
    id: 'gpt-5.2',
    name: 'GPT-5.2',
    provider: 'openai',
    hasVision: true,
    tier: 'flagship',
    description: 'Latest flagship model with multimodal support',
  },
  {
    id: 'gpt-5.2-pro',
    name: 'GPT-5.2 Pro',
    provider: 'openai',
    hasVision: true,
    tier: 'flagship',
    description: 'Highest quality model for complex reasoning',
  },
  {
    id: 'gpt-5.2-chat-latest',
    name: 'GPT-5.2 Chat Latest',
    provider: 'openai',
    hasVision: true,
    tier: 'standard',
    description: 'Latest chat-tuned model for general workflows',
  },
  {
    id: 'gpt-5-mini',
    name: 'GPT-5 Mini',
    provider: 'openai',
    hasVision: true,
    tier: 'efficient',
    description: 'Faster, cost-optimized model for high volume work',
  },
  {
    id: 'gpt-5-nano',
    name: 'GPT-5 Nano',
    provider: 'openai',
    hasVision: true,
    tier: 'efficient',
    description: 'Ultra-lightweight model for quick tasks',
  },

  // Anthropic Models
  {
    id: 'claude-opus-4-5',
    name: 'Claude Opus 4.5',
    provider: 'anthropic',
    hasVision: true,
    tier: 'flagship',
    description: 'Most capable Claude model for complex tasks',
  },
  {
    id: 'claude-sonnet-4-5',
    name: 'Claude Sonnet 4.5',
    provider: 'anthropic',
    hasVision: true,
    tier: 'standard',
    description: 'Balanced model for quality and speed',
  },
  {
    id: 'claude-haiku-4-5',
    name: 'Claude Haiku 4.5',
    provider: 'anthropic',
    hasVision: true,
    tier: 'efficient',
    description: 'Fast and cost-effective Claude model',
  },

  // Google Gemini Models
  {
    id: 'gemini-3-pro-preview',
    name: 'Gemini 3 Pro Preview',
    provider: 'google',
    hasVision: true,
    tier: 'flagship',
    description: 'Latest reasoning-first model for complex tasks',
    contextTokens: 1048576,
  },
  {
    id: 'gemini-3-flash-preview',
    name: 'Gemini 3 Flash Preview',
    provider: 'google',
    hasVision: true,
    tier: 'standard',
    description: 'Fast multimodal model with strong reasoning',
    contextTokens: 1048576,
  },
  {
    id: 'gemini-2.5-pro',
    name: 'Gemini 2.5 Pro',
    provider: 'google',
    hasVision: true,
    tier: 'flagship',
    description: 'Stable flagship with advanced reasoning',
    contextTokens: 1048576,
  },
  {
    id: 'gemini-2.5-flash',
    name: 'Gemini 2.5 Flash',
    provider: 'google',
    hasVision: true,
    tier: 'standard',
    description: 'Stable fast model with large context',
    contextTokens: 1048576,
  },
  {
    id: 'gemini-2.0-flash',
    name: 'Gemini 2.0 Flash',
    provider: 'google',
    hasVision: true,
    tier: 'efficient',
    description: 'Fast and efficient Gemini model',
    contextTokens: 1048576,
  },

  // Mistral Models
  {
    id: 'mistral-large-latest',
    name: 'Mistral Large',
    provider: 'mistral',
    hasVision: false,
    tier: 'flagship',
    description: 'Highest quality Mistral text model',
  },
  {
    id: 'mistral-medium-latest',
    name: 'Mistral Medium',
    provider: 'mistral',
    hasVision: false,
    tier: 'standard',
    description: 'Balanced Mistral text model',
  },
  {
    id: 'mistral-small-latest',
    name: 'Mistral Small',
    provider: 'mistral',
    hasVision: false,
    tier: 'efficient',
    description: 'Fast, cost-optimized Mistral model',
  },
  {
    id: 'devstral-latest',
    name: 'Devstral',
    provider: 'mistral',
    hasVision: false,
    tier: 'efficient',
    description: 'Developer-focused model for code tasks',
  },

  // OpenRouter Models
  {
    id: 'openai/gpt-5.2',
    name: 'OpenRouter GPT-5.2',
    provider: 'openrouter',
    hasVision: true,
    tier: 'flagship',
    description: 'OpenRouter access to OpenAI GPT-5.2',
  },
  {
    id: 'google/gemini-3-pro-preview',
    name: 'OpenRouter Gemini 3 Pro',
    provider: 'openrouter',
    hasVision: true,
    tier: 'flagship',
    description: 'OpenRouter access to Gemini 3 Pro Preview',
  },
  {
    id: 'anthropic/claude-opus-4-5',
    name: 'OpenRouter Claude Opus 4.5',
    provider: 'openrouter',
    hasVision: true,
    tier: 'flagship',
    description: 'OpenRouter access to Claude Opus 4.5',
  },
  {
    id: 'google/gemma-3-27b-it:free',
    name: 'OpenRouter Google Gemma 3 27B (free)',
    provider: 'openrouter',
    hasVision: true,
    tier: 'efficient',
    description: 'Gemma 3 27B hosted via OpenRouter',
    inputCost: '$0',
    outputCost: '$0',
    contextTokens: 131072,
  },
  {
    id: 'nvidia/nemotron-nano-12b-v2-vl:free',
    name: 'OpenRouter NVIDIA Nemotron Nano 12B 2 VL (free)',
    provider: 'openrouter',
    hasVision: true,
    tier: 'efficient',
    description: 'OpenRouter Nvidia Nimotron Nano',
    inputCost: '$0',
    outputCost: '$0',
    contextTokens: 128000,
  },
  {
    id: 'google/gemini-2.0-flash-exp:free',
    name: 'OpenRouter Gemini 2.0 Flash Exp (free)',
    provider: 'openrouter',
    hasVision: true,
    tier: 'efficient',
    description: 'Gemini 2.0 Flash Experimental free tier',
    inputCost: '$0',
    outputCost: '$0',
    contextTokens: 1048576,
  },
  {
    id: 'mistralai/mistral-small-3.1-24b-instruct:free',
    name: 'OpenRouter Mistral Small 3.1 24B (free)',
    provider: 'openrouter',
    hasVision: false,
    tier: 'efficient',
    description: 'Mistral Small 3.1 hosted by OpenRouter',
    inputCost: '$0',
    outputCost: '$0',
    contextTokens: 128000,
  },
  {
    id: 'meta-llama/llama-4-maverick',
    name: 'OpenRouter Llama 4 Maverick',
    provider: 'openrouter',
    hasVision: false,
    tier: 'standard',
    description: 'Llama 4 Maverick with deep context',
    inputCost: '$0.15/M',
    outputCost: '$0.60/M',
    contextTokens: 1048576,
  },
  {
    id: 'meta-llama/llama-4-scout',
    name: 'OpenRouter Llama 4 Scout',
    provider: 'openrouter',
    hasVision: false,
    tier: 'efficient',
    description: 'Llama 4 Scout with up to 327k context',
    inputCost: '$0.08/M',
    outputCost: '$0.30/M',
    contextTokens: 327680,
  },
  {
    id: 'qwen/qwen3-next-80b-a3b-instruct',
    name: 'OpenRouter Qwen3 Next 80B',
    provider: 'openrouter',
    hasVision: false,
    tier: 'flagship',
    description: 'Large assistant tuned for general text',
    inputCost: '$0.09/M',
    outputCost: '$1.10/M',
    contextTokens: 262144,
  },
  {
    id: 'qwen/qwen3-32b',
    name: 'OpenRouter Qwen3 32B',
    provider: 'openrouter',
    hasVision: false,
    tier: 'standard',
    description: 'Balanced 32B model with higher throughput',
    inputCost: '$0.08/M',
    outputCost: '$0.24/M',
    contextTokens: 40960,
  },
  {
    id: 'qwen/qwen3-14b',
    name: 'OpenRouter Qwen3 14B',
    provider: 'openrouter',
    hasVision: false,
    tier: 'efficient',
    description: 'Cost-effective 14B model for text',
    inputCost: '$0.05/M',
    outputCost: '$0.22/M',
    contextTokens: 40960,
  },
  {
    id: 'qwen/qwen3-8b',
    name: 'OpenRouter Qwen3 8B',
    provider: 'openrouter',
    hasVision: false,
    tier: 'efficient',
    description: 'Compact Qwen3 with 128k context',
    inputCost: '$0.035/M',
    outputCost: '$0.138/M',
    contextTokens: 128000,
  },
  {
    id: 'qwen/qwen3-coder',
    name: 'OpenRouter Qwen3 Coder',
    provider: 'openrouter',
    hasVision: false,
    tier: 'standard',
    description: 'Coding specialist with 262k context',
    inputCost: '$0.22/M',
    outputCost: '$0.95/M',
    contextTokens: 262144,
  },
  {
    id: 'qwen/qwen3-vl-30b-a3b-instruct',
    name: 'OpenRouter Qwen3 VL 30B',
    provider: 'openrouter',
    hasVision: true,
    tier: 'flagship',
    description: 'Vision-tuned 30B Qwen3 with large context',
    inputCost: '$0.15/M',
    outputCost: '$0.60/M',
    contextTokens: 262144,
  },
  {
    id: 'qwen/qwen3-vl-235b-a22b-instruct',
    name: 'OpenRouter Qwen3 VL 235B Instruct',
    provider: 'openrouter',
    hasVision: true,
    tier: 'flagship',
    description: 'High-capacity vision model for documents',
    inputCost: '$0.20/M',
    outputCost: '$1.20/M',
    contextTokens: 262144,
  },
  {
    id: 'qwen/qwen3-vl-235b-a22b-thinking',
    name: 'OpenRouter Qwen3 VL 235B Thinking',
    provider: 'openrouter',
    hasVision: true,
    tier: 'flagship',
    description: 'Vision reasoning flavor with premium quality',
    inputCost: '$0.45/M',
    outputCost: '$3.50/M',
    contextTokens: 262144,
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
  mistral_api_key: string;
  openrouter_api_key: string;
  mistral_base_url: string;
  openrouter_base_url: string;
  ollama_base_url: string;
  default_provider: 'openai' | 'anthropic' | 'google' | 'mistral' | 'openrouter' | 'ollama';
  vision_model: string;
  text_model: string;
  max_cards_per_slide: number;
  auto_dedupe: boolean;
}

const PROVIDER_METADATA_NOTES: Record<Settings['default_provider'], string> = {
  openai:
    'OpenAI /models provides only model IDs; refer to the model comparison docs for context/pricing.',
  anthropic:
    'Claude /models returns IDs/display names only; consult Anthropic pricing pages for costs.',
  google:
    'Gemini /models exposes context limits (input/output), but pricing comes from Google Cloud docs.',
  mistral:
    'Mistral /models returns max_context_length; pricing is detailed in their pricing guide.',
  openrouter:
    'OpenRouter /models exposes context_length plus pricing for the routed provider.',
  ollama:
    'Ollama /api/models returns local metadata; pricing is controlled by your local deployment.',
};

type Provider = Settings['default_provider'];

const toNumberValue = (value: unknown): number | undefined => {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? undefined : parsed;
  }
  return undefined;
};

const formatPricingValue = (value: unknown): string | undefined => {
  if (value == null) {
    return undefined;
  }
  if (typeof value === 'string') {
    return value.trim();
  }
  if (typeof value === 'number') {
    return `${value}`;
  }
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const amount =
      toNumberValue(record.amount) ??
      toNumberValue(record.price) ??
      toNumberValue(record.value);
    const unit = typeof record.unit === 'string' ? record.unit : ' per unit';
    if (amount != null) {
      return `${amount}${unit}`;
    }
    const entries = Object.entries(record)
      .filter(([, entry]) => entry != null && entry !== '')
      .map(([key, entry]) => `${key}: ${String(entry)}`);
    if (entries.length) {
      return entries.join(', ');
    }
  }
  return undefined;
};

const modelsArrayFromResponse = (body: unknown): unknown[] | null => {
  if (Array.isArray(body)) {
    return body;
  }
  if (!body || typeof body !== 'object') {
    return null;
  }
  const record = body as Record<string, unknown>;
  if (Array.isArray(record.models)) {
    return record.models;
  }
  if (Array.isArray(record.data)) {
    return record.data;
  }
  if (Array.isArray(record.modelInfo)) {
    return record.modelInfo;
  }
  return null;
};

const extractMetadata = (
  provider: Provider,
  body: unknown
): ModelMetadataEntry[] | null => {
  const models = modelsArrayFromResponse(body);
  if (!models?.length) {
    return null;
  }

  const baseList = models.slice(0, 8);

  return baseList.map((modelObj) => {
    if (!modelObj || typeof modelObj !== 'object') {
      return null;
    }
    const model = modelObj as Record<string, unknown>;
    const id = (model.id as string) || (model.name as string) || '';
    const name =
      (model.name && typeof model.name === 'string'
        ? model.name
        : model.display_name && typeof model.display_name === 'string'
        ? model.display_name
        : id) || undefined;
    const contextTokens =
      toNumberValue(model.context_length) ??
      toNumberValue(model.max_context_length) ??
      toNumberValue(model.inputTokenLimit) ??
      toNumberValue(model.outputTokenLimit);

    const pricing =
      provider === 'openrouter'
        ? model.pricing
        : provider === 'openai'
        ? model.limits
        : undefined;

    const entry: ModelMetadataEntry = {
      id: id || (model.name as string) || '',
      name,
      contextTokens: contextTokens ?? undefined,
    };

    if (provider === 'openrouter') {
      entry.inputCost = formatPricingValue(
        (model.pricing as Record<string, unknown>)?.input
      );
      entry.outputCost = formatPricingValue(
        (model.pricing as Record<string, unknown>)?.output
      );
    } else if (pricing) {
      entry.inputCost = formatPricingValue(
        (pricing as Record<string, unknown>)?.input
      );
      entry.outputCost = formatPricingValue(
        (pricing as Record<string, unknown>)?.output
      );
    }

    if (provider === 'google' && model.outputTokenLimit) {
      entry.note = `Output limit: ${model.outputTokenLimit}`;
    }

    if (!entry.id) {
      return null;
    }

    return entry;
  }).filter((entry): entry is ModelMetadataEntry => Boolean(entry));
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    openai_api_key: '',
    anthropic_api_key: '',
    google_api_key: '',
    mistral_api_key: '',
    openrouter_api_key: '',
    mistral_base_url: 'https://api.mistral.ai/v1',
    openrouter_base_url: 'https://openrouter.ai/api/v1',
    ollama_base_url: 'http://localhost:11434',
    default_provider: 'openai',
    vision_model: 'gpt-5.2',
    text_model: 'gpt-5.2',
    max_cards_per_slide: 5,
    auto_dedupe: true,
  });
  const [saved, setSaved] = useState(false);
  const [persistedSettings, setPersistedSettings] = useState<AppSettings | null>(
    null
  );
  const [saveStatus, setSaveStatus] = useState<PingStatus>('idle');
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [pingStatus, setPingStatus] = useState<PingStatus>('idle');
  const [pingMessage, setPingMessage] = useState<string | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);
  const [modelMetadata, setModelMetadata] = useState<ModelMetadataEntry[] | null>(null);
  const [metadataHint, setMetadataHint] = useState<string | null>(null);
  const [metadataFetched, setMetadataFetched] = useState(false);
  const [modelPingStatus, setModelPingStatus] = useState<PingStatus>('idle');
  const [modelPingResponse, setModelPingResponse] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('slide2anki_settings');
    if (!stored) {
      // Still hydrate even if localStorage is empty so we can fetch persisted settings.
      setIsHydrated(true);
      return;
    }
    try {
      const parsed = JSON.parse(stored) as Partial<Settings>;
      setSettings((current) => ({
        ...current,
        ...parsed,
      }));
    } catch {
      // Keep defaults if parsing fails
    } finally {
      setIsHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    let active = true;
    api
      .getSettings()
      .then((data) => {
        if (!active) {
          return;
        }
        setPersistedSettings(data);
        setSettings((current) => {
          const provider = (data.provider as Settings['default_provider']) || current.default_provider;
          const model = data.model || current.vision_model;
          const next = { ...current, default_provider: provider, vision_model: model, text_model: model };
          if (data.base_url) {
            if (provider === 'openrouter') {
              next.openrouter_base_url = data.base_url;
            } else if (provider === 'mistral') {
              next.mistral_base_url = data.base_url;
            } else if (provider === 'ollama') {
              next.ollama_base_url = data.base_url;
            }
          }
          return next;
        });
      })
      .catch(() => {
        if (active) {
          setPersistedSettings(null);
        }
      });

    return () => {
      active = false;
    };
  }, [isHydrated]);

  useEffect(() => {
    setPingStatus('idle');
    setPingMessage(null);
    setModelMetadata(null);
    setMetadataHint(null);
    setMetadataFetched(false);
    setModelPingStatus('idle');
    setModelPingResponse(null);
    setSaveStatus('idle');
    setSaveMessage(null);
  }, [settings.default_provider]);

  if (!isHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-500">
        Loading settings…
      </div>
    );
  }

  const handleSave = () => {
    setSaveStatus('idle');
    setSaveMessage(null);
    localStorage.setItem('slide2anki_settings', JSON.stringify(settings));
    const provider = settings.default_provider;
    const model = settings.vision_model || settings.text_model;

    const keyByProvider: Record<string, string> = {
      openai: settings.openai_api_key,
      anthropic: settings.anthropic_api_key,
      google: settings.google_api_key,
      mistral: settings.mistral_api_key,
      openrouter: settings.openrouter_api_key,
      ollama: '',
    };

    const baseUrlByProvider: Record<string, string | null> = {
      openai: null,
      anthropic: null,
      google: null,
      mistral: sanitizeBaseUrl(settings.mistral_base_url || ''),
      openrouter: sanitizeBaseUrl(settings.openrouter_base_url || ''),
      ollama: sanitizeBaseUrl(settings.ollama_base_url || ''),
    };

    const apiKey = (keyByProvider[provider] || '').trim();
    const baseUrl = baseUrlByProvider[provider] || null;

    const errors: string[] = [];
    if (!provider) {
      errors.push('Select a provider.');
    }
    if (!model) {
      errors.push('Select a model.');
    }

    const hasStoredKeyForProvider =
      persistedSettings?.provider === provider && persistedSettings.api_key_present;

    if (provider === 'openrouter') {
      if (!baseUrl) {
        errors.push('Provide an OpenRouter base URL.');
      }
      if (!apiKey && !hasStoredKeyForProvider) {
        errors.push('Provide an OpenRouter API key.');
      }
    }

    if (provider === 'openai') {
      if (!apiKey && !hasStoredKeyForProvider) {
        errors.push('Provide an OpenAI API key.');
      }
    }

    if (provider === 'ollama') {
      if (!baseUrl) {
        errors.push('Provide an Ollama base URL.');
      }
    }

    if (errors.length > 0) {
      setSaveStatus('error');
      setSaveMessage(errors.join(' '));
      return;
    }

    setSaveStatus('loading');
    setSaveMessage('Saving settings...');

    api
      .updateSettings({
        provider,
        model,
        base_url: baseUrl,
        ...(apiKey ? { api_key: apiKey } : {}),
      })
      .then((data) => {
        setPersistedSettings(data);
        setSaveStatus('success');
        setSaveMessage(
          `Saved to backend at ${new Date(data.updated_at).toLocaleString()}.`
        );
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      })
      .catch((error) => {
        setSaved(false);
        setSaveStatus('error');
        setSaveMessage(
          error instanceof Error
            ? `Failed to save settings: ${error.message}`
            : 'Failed to save settings.'
        );
      });
  };

  const sanitizeBaseUrl = (value: string) =>
    value ? value.replace(/\/+$/, '') : '';

  const describeBody = (body: unknown) => {
    if (body == null) {
      return 'no payload';
    }
    if (typeof body === 'string') {
      return body.slice(0, 120);
    }
    try {
      const text = JSON.stringify(body);
      return text.length > 120 ? `${text.slice(0, 120)}…` : text;
    } catch {
      return 'response payload';
    }
  };

  const buildPingRequest = () => {
    const provider = settings.default_provider;
    switch (provider) {
      case 'openai': {
        const key = settings.openai_api_key.trim();
        if (!key) {
          return { error: 'Provide an OpenAI API key before pinging.' };
        }
        return {
          url: 'https://api.openai.com/v1/models',
          options: {
            method: 'GET',
            headers: new Headers({
              Authorization: `Bearer ${key}`,
            }),
          },
        };
      }
      case 'anthropic': {
        const key = settings.anthropic_api_key.trim();
        if (!key) {
          return { error: 'Provide an Anthropic API key before pinging.' };
        }
        return {
          url: 'https://api.anthropic.com/v1/models',
          options: {
            method: 'GET',
            headers: new Headers({
              'x-api-key': key,
            }),
          },
        };
      }
      case 'google': {
        const key = settings.google_api_key.trim();
        if (!key) {
          return { error: 'Provide a Google AI API key before pinging.' };
        }
        return {
          url: `https://generativelanguage.googleapis.com/v1beta/models?key=${key}`,
          options: {
            method: 'GET',
          },
        };
      }
      case 'mistral': {
        const key = settings.mistral_api_key.trim();
        if (!key) {
          return { error: 'Provide a Mistral API key before pinging.' };
        }
        const base = sanitizeBaseUrl(settings.mistral_base_url || '');
        if (!base) {
          return { error: 'Provide a Mistral base URL.' };
        }
        return {
          url: `${base}/models`,
          options: {
            method: 'GET',
            headers: new Headers({
              Authorization: `Bearer ${key}`,
            }),
          },
        };
      }
      case 'openrouter': {
        const key = settings.openrouter_api_key.trim();
        if (!key) {
          return { error: 'Provide an OpenRouter API key before pinging.' };
        }
        const base = sanitizeBaseUrl(settings.openrouter_base_url || '');
        if (!base) {
          return { error: 'Provide an OpenRouter base URL.' };
        }
        return {
          url: `${base}/models`,
          options: {
            method: 'GET',
            headers: new Headers({
              Authorization: `Bearer ${key}`,
            }),
          },
        };
      }
      case 'ollama': {
        const base = sanitizeBaseUrl(settings.ollama_base_url);
        if (!base) {
          return { error: 'Provide an Ollama base URL before pinging.' };
        }
        return {
          url: `${base}/api/models`,
          options: {
            method: 'GET',
          },
        };
      }
      default:
        return { error: 'Unsupported provider for ping.' };
    }
  };

  const handlePing = async () => {
    const requestOrError = buildPingRequest();
    if ('error' in requestOrError) {
      setPingStatus('error');
      setPingMessage(requestOrError.error ?? 'Unable to ping provider.');
      return;
    }

    setPingStatus('loading');
    setPingMessage('Pinging provider...');
    setMetadataFetched(false);
    setMetadataHint(null);
    setModelMetadata(null);

    try {
      const response = await fetch(requestOrError.url, requestOrError.options);
      if (!response.ok) {
        throw new Error(`Ping failed: ${response.status}`);
      }
      const body = await response.json().catch(() => null);
      setPingStatus('success');
      setPingMessage(
        `Success (${response.status}): ${describeBody(body)}`
      );
      const metadata = extractMetadata(settings.default_provider, body);
      setModelMetadata(metadata);
      setMetadataHint(
        metadata
          ? null
          : PROVIDER_METADATA_NOTES[settings.default_provider] ??
            'Provider did not return model metadata.'
      );
      setMetadataFetched(true);
    } catch (error) {
      setPingStatus('error');
      const message =
        error instanceof Error ? error.message : 'Ping failed unexpectedly';
      setPingMessage(message);
    }
  };

  /*
   * Build a model invocation request for the selected provider/model.
   * Returns { url, options } suitable for fetch, or { error } string.
   */
  type ModelPingRequest = { url: string; options: RequestInit } | { error: string };

  const buildModelPingRequest = (): ModelPingRequest => {
    const provider = settings.default_provider;
    const model = settings.text_model || settings.vision_model;
    const testPrompt = 'Ping from slide2anki - please reply: pong';

    switch (provider) {
      case 'openai': {
        const key = settings.openai_api_key.trim();
        if (!key) {
          return { error: 'Provide an OpenAI API key before pinging a model.' };
        }
        // Use Responses API when available, fallback to completions
        const body = { model, input: testPrompt };
        return {
          url: 'https://api.openai.com/v1/responses',
          options: {
            method: 'POST',
            headers: new Headers({
              Authorization: `Bearer ${key}`,
              'Content-Type': 'application/json',
            }),
            body: JSON.stringify(body),
          },
        };
      }
      case 'anthropic': {
        const key = settings.anthropic_api_key.trim();
        if (!key) {
          return { error: 'Provide an Anthropic API key before pinging a model.' };
        }
        // Use /v1/complete style with simple prompt as a robust fallback
        const body = { model, prompt: `Human: ${testPrompt}\nAssistant:` };
        return {
          url: 'https://api.anthropic.com/v1/complete',
          options: {
            method: 'POST',
            headers: new Headers({
              'x-api-key': key,
              'Content-Type': 'application/json',
            }),
            body: JSON.stringify(body),
          },
        };
      }
      case 'google': {
        const key = settings.google_api_key.trim();
        if (!key) {
          return { error: 'Provide a Google AI API key before pinging a model.' };
        }
        // Use the generativelanguage generateContent endpoint for Gemini models
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
        const body = { contents: [{ parts: [{ text: testPrompt }] }] };
        return {
          url,
          options: {
            method: 'POST',
            headers: new Headers({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
          },
        };
      }
      case 'mistral': {
        const key = settings.mistral_api_key.trim();
        if (!key) {
          return { error: 'Provide a Mistral API key before pinging a model.' };
        }
        const base = sanitizeBaseUrl(settings.mistral_base_url || '');
        if (!base) {
          return { error: 'Provide a Mistral base URL.' };
        }
        // Try the common /v1/generate endpoint
        const url = `${base}/v1/generate`;
        const body = { model, input: testPrompt };
        return {
          url,
          options: {
            method: 'POST',
            headers: new Headers({
              Authorization: `Bearer ${key}`,
              'Content-Type': 'application/json',
            }),
            body: JSON.stringify(body),
          },
        };
      }
      case 'openrouter': {
        const key = settings.openrouter_api_key.trim();
        if (!key) {
          return { error: 'Provide an OpenRouter API key before pinging a model.' };
        }
        const base = sanitizeBaseUrl(settings.openrouter_base_url || '');
        if (!base) {
          return { error: 'Provide an OpenRouter base URL.' };
        }
        const body = { model, input: testPrompt };
        // OpenRouter commonly accepts /chat/completions or /responses; try /responses
        return {
          url: `${base}/responses`,
          options: {
            method: 'POST',
            headers: new Headers({
              Authorization: `Bearer ${key}`,
              'Content-Type': 'application/json',
            }),
            body: JSON.stringify(body),
          },
        };
      }
      case 'ollama': {
        const base = sanitizeBaseUrl(settings.ollama_base_url);
        if (!base) {
          return { error: 'Provide an Ollama base URL before pinging a model.' };
        }
        const body = { model, prompt: testPrompt };
        return {
          url: `${base}/api/generate`,
          options: {
            method: 'POST',
            headers: new Headers({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
          },
        };
      }
      default:
        return { error: 'Unsupported provider for model ping.' };
    }
  };

  const handleModelPing = async () => {
    const req = buildModelPingRequest();
    if ('error' in req) {
      setModelPingStatus('error');
      setModelPingResponse(req.error ?? 'Unable to ping model.');
      return;
    }

    setModelPingStatus('loading');
    setModelPingResponse('Sending test prompt...');

    try {
      const res = await fetch(req.url, req.options);
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`Model ping failed: ${res.status} ${text}`);
      }
      // Try to extract a response text from common API shapes
      const body = await res.json().catch(() => null);
      let text = 'No text in response';
      if (!body) {
        text = 'Empty response';
      } else if (typeof body === 'string') {
        text = body;
      } else if (Array.isArray((body as any).outputs) && (body as any).outputs[0]?.content) {
        text = (body as any).outputs[0].content[0]?.text || JSON.stringify(body.outputs[0]);
      } else if ((body as any).output && typeof (body as any).output === 'string') {
        text = (body as any).output;
      } else if ((body as any).choices && Array.isArray((body as any).choices)) {
        const choice = (body as any).choices[0];
        text = choice?.message?.content?.[0]?.text || choice?.text || JSON.stringify(choice);
      } else if ((body as any).result && (body as any).result[0]) {
        text = String((body as any).result[0]);
      } else if ((body as any).completion) {
        text = String((body as any).completion);
      } else {
        // Generic fallback: stringify a short part of the body
        try {
          const s = JSON.stringify(body);
          text = s.length > 1000 ? `${s.slice(0, 1000)}…` : s;
        } catch {
          text = 'Received non-JSON response';
        }
      }

      setModelPingStatus('success');
      setModelPingResponse(text);
    } catch (err) {
      setModelPingStatus('error');
      setModelPingResponse(err instanceof Error ? err.message : 'Ping failed');
    }
  };

  const getModelsForProvider = (provider: string) =>
    AVAILABLE_MODELS.filter((m) => m.provider === provider);

  const getVisionModels = () =>
    AVAILABLE_MODELS.filter(
      (m) => m.provider === settings.default_provider && m.hasVision
    );

  const getTextModels = () =>
    AVAILABLE_MODELS.filter((m) => m.provider === settings.default_provider);

  const visionModels = getVisionModels();
  const textModels = getTextModels();
  const selectedModel =
    AVAILABLE_MODELS.find((model) => model.id === settings.text_model) ??
    AVAILABLE_MODELS.find((model) => model.id === settings.vision_model);

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

      <div className="mb-6 rounded-lg border bg-white p-4">
        <p className="text-sm font-semibold text-gray-900">
          Worker configuration status
        </p>
        <p className="mt-1 text-sm text-gray-600">
          The worker reads provider settings from the backend database. API keys
          are masked in the UI.
        </p>
        {persistedSettings ? (
          <div className="mt-3 grid gap-2 text-sm text-gray-700 sm:grid-cols-2">
            <div>
              <span className="text-gray-500">Provider:</span>{' '}
              {persistedSettings.provider}
            </div>
            <div>
              <span className="text-gray-500">Model:</span>{' '}
              {persistedSettings.model || 'Not set'}
            </div>
            <div className="sm:col-span-2">
              <span className="text-gray-500">Base URL:</span>{' '}
              {persistedSettings.base_url || 'Default'}
            </div>
            <div>
              <span className="text-gray-500">API key:</span>{' '}
              {persistedSettings.api_key_present ? 'Stored (masked)' : 'Not set'}
            </div>
            <div>
              <span className="text-gray-500">Updated:</span>{' '}
              {new Date(persistedSettings.updated_at).toLocaleString()}
            </div>
          </div>
        ) : (
          <p className="mt-3 text-sm text-gray-600">
            Backend settings not loaded. Make sure the API is running.
          </p>
        )}
      </div>

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
                  const visionModel =
                    providerModels.find((m) => m.hasVision)?.id || '';
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
                <option value="mistral">Mistral</option>
                <option value="openrouter">OpenRouter</option>
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
                {visionModels.length === 0 ? (
                  <option value="" disabled>
                    No vision models available for this provider
                  </option>
                ) : (
                  visionModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} - {model.description}
                    </option>
                  ))
                )}
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
                {textModels.map((model) => (
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
            {selectedModel && (
              <div className="mt-4 p-3 bg-white rounded-lg border">
                <p className="text-xs text-gray-500 mb-1">Selected model limits</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 text-xs">
                  <div>
                    <strong className="block text-gray-700">Input cost</strong>
                    <span className="text-gray-600">
                      {selectedModel.inputCost ?? 'Custom'}
                    </span>
                  </div>
                  <div>
                    <strong className="block text-gray-700">Output cost</strong>
                    <span className="text-gray-600">
                      {selectedModel.outputCost ?? 'Custom'}
                    </span>
                  </div>
                  <div>
                    <strong className="block text-gray-700">Context</strong>
                    <span className="text-gray-600">
                      {selectedModel.contextTokens
                        ? `${selectedModel.contextTokens.toLocaleString()} tokens`
                        : 'Varies'}
                    </span>
                  </div>
                </div>
              </div>
            )}
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mistral API Key
              </label>
              <input
                type="password"
                value={settings.mistral_api_key}
                onChange={(e) =>
                  setSettings({ ...settings, mistral_api_key: e.target.value })
                }
                placeholder="mistral-..."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                OpenRouter API Key
              </label>
              <input
                type="password"
                value={settings.openrouter_api_key}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    openrouter_api_key: e.target.value,
                  })
                }
                placeholder="or-..."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                {persistedSettings?.provider === 'openrouter' &&
                persistedSettings.api_key_present
                  ? 'An API key is already stored (masked). Leave this blank to keep the current key.'
                  : 'Required when using OpenRouter.'}
              </p>
            </div>

            <p className="text-xs text-gray-500">
              API keys are stored in your local Postgres container so the worker can use them. They are never sent anywhere except your selected provider.
            </p>
          </div>
        </div>

        {/* Provider Endpoints */}
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Provider Endpoints</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mistral Base URL
              </label>
              <input
                type="text"
                value={settings.mistral_base_url}
                onChange={(e) =>
                  setSettings({ ...settings, mistral_base_url: e.target.value })
                }
                placeholder="https://api.mistral.ai/v1"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                OpenRouter Base URL
              </label>
              <input
                type="text"
                value={settings.openrouter_base_url}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    openrouter_base_url: e.target.value,
                  })
                }
                placeholder="https://openrouter.ai/api/v1"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
        </div>
      </div>

      <div className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Wifi className="w-5 h-5 text-gray-500" />
          <h2 className="font-semibold text-gray-900">Ping provider endpoint</h2>
        </div>
        <p className="text-sm text-gray-600 mb-3">
          Verify the currently selected provider responds before running pipelines.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={pingStatus === 'loading'}
            onClick={handlePing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg border text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {pingStatus === 'loading' ? 'Pinging…' : `Ping ${settings.default_provider}`}
          </button>
          <button
            type="button"
            disabled={modelPingStatus === 'loading'}
            onClick={handleModelPing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg border text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {modelPingStatus === 'loading'
              ? 'Pinging model…'
              : `Ping model (${selectedModel?.name ?? settings.text_model})`}
          </button>
        </div>
        {pingMessage && (
          <p
            className={`mt-3 text-sm ${
              pingStatus === 'success'
                ? 'text-green-700'
                : pingStatus === 'error'
                ? 'text-red-600'
                : 'text-gray-600'
            }`}
            aria-live="polite"
          >
            {pingMessage}
          </p>
        )}
        {modelPingResponse && (
          <p
            className={`mt-3 text-sm ${
              modelPingStatus === 'success'
                ? 'text-green-700'
                : modelPingStatus === 'error'
                ? 'text-red-600'
                : 'text-gray-600'
            }`}
            aria-live="polite"
          >
            {modelPingResponse}
          </p>
        )}
        {metadataFetched && (modelMetadata?.length || metadataHint) && (
          <div className="mt-4 space-y-3">
            {modelMetadata && modelMetadata.length > 0 ? (
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">
                  Latest metadata from {settings.default_provider}
                </p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {modelMetadata.map((entry) => (
                    <div
                      key={entry.id}
                      className="p-3 bg-gray-50 rounded-lg border text-xs text-gray-700 space-y-1"
                    >
                      <p className="font-semibold text-gray-900 text-sm">
                        {entry.name ?? entry.id}
                      </p>
                      <p className="text-gray-500">
                        ID: {entry.id}
                        {entry.contextTokens
                          ? ` · ${entry.contextTokens.toLocaleString()} tokens`
                          : ''}
                      </p>
                      <div className="flex flex-wrap gap-2 text-gray-600">
                        {entry.inputCost && (
                          <span className="text-[11px] rounded bg-white px-2 py-1 border">
                            Input: {entry.inputCost}
                          </span>
                        )}
                        {entry.outputCost && (
                          <span className="text-[11px] rounded bg-white px-2 py-1 border">
                            Output: {entry.outputCost}
                          </span>
                        )}
                      </div>
                      {entry.note && (
                        <p className="text-[11px] text-gray-500">{entry.note}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              metadataHint && (
                <p className="text-sm text-gray-500">{metadataHint}</p>
              )
            )}
          </div>
        )}
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
        {saveMessage ? (
          <span
            className={`text-sm ${
              saveStatus === 'success'
                ? 'text-green-700'
                : saveStatus === 'error'
                ? 'text-red-600'
                : 'text-gray-600'
            }`}
            aria-live="polite"
          >
            {saveMessage}
          </span>
        ) : saved ? (
          <span className="text-sm text-green-700">Settings saved.</span>
        ) : null}
        <button
          onClick={handleSave}
          disabled={saveStatus === 'loading'}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <Save className="w-4 h-4" />
          {saveStatus === 'loading' ? 'Saving…' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
