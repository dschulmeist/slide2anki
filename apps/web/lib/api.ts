/**
 * Typed API client for the slide2anki backend.
 * Uses relative URLs in the browser (proxied by Next.js rewrites) and internal Docker URL for SSR.
 */
const SERVER_API_BASE = process.env.API_INTERNAL_URL || 'http://api:8000';
// In browser, use empty string for relative URLs - Next.js rewrites will proxy to API
const CLIENT_API_BASE = '';

const resolveApiBase = (): string => {
  return typeof window === 'undefined' ? SERVER_API_BASE : CLIENT_API_BASE;
};

export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  deck_count: number;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  object_key: string;
  page_count: number;
  created_at: string;
}

export interface Chapter {
  id: string;
  project_id: string;
  title: string;
  position_index: number;
}

export interface MarkdownVersion {
  id: string;
  project_id: string;
  version: number;
  content: string;
  created_at: string;
  created_by?: string | null;
}

export interface MarkdownBlock {
  id: string;
  project_id: string;
  chapter_id: string;
  anchor_id: string;
  kind: string;
  content: string;
  evidence_json?: unknown[] | null;
  position_index: number;
}

export interface Deck {
  id: string;
  project_id: string;
  chapter_id?: string | null;
  name: string;
  status: string;
  created_at: string;
  card_count: number;
  pending_review: number;
}

export interface Job {
  id: string;
  project_id: string;
  document_id?: string | null;
  deck_id?: string | null;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step?: string | null;
  error_message?: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface JobEvent {
  id: string;
  job_id: string;
  level: string;
  message: string;
  step?: string | null;
  progress?: number | null;
  details_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface CardDraft {
  id: string;
  deck_id: string;
  anchor_id?: string | null;
  front: string;
  back: string;
  tags: string[];
  confidence: number;
  flags_json?: unknown[] | null;
  evidence_json?: unknown[] | null;
  status: 'pending' | 'approved' | 'rejected';
}

export interface CardRevision {
  id: string;
  card_id: string;
  revision_number: number;
  front: string;
  back: string;
  tags: string[];
  edited_by?: string | null;
  created_at: string;
}

export interface Slide {
  id: string;
  document_id: string;
  page_index: number;
  image_object_key: string;
  image_url?: string | null;
}

export interface AppSettings {
  provider: string;
  model: string;
  base_url?: string | null;
  api_key_present: boolean;
  updated_at: string;
}

export interface AppSettingsUpdate {
  provider: string;
  model: string;
  base_url?: string | null;
  api_key?: string;
}

interface ProjectListResponse {
  projects: Project[];
}

interface DocumentListResponse {
  documents: Document[];
}

interface ChapterListResponse {
  chapters: Chapter[];
}

interface DeckListResponse {
  decks: Deck[];
}

interface JobListResponse {
  jobs: Job[];
}

interface JobEventListResponse {
  events: JobEvent[];
}

interface CardDraftListResponse {
  cards: CardDraft[];
}

interface CardRevisionListResponse {
  revisions: CardRevision[];
}

interface SlideListResponse {
  slides: Slide[];
}

interface DocumentUploadResponse {
  document_id: string;
  project_id: string;
  filename: string;
  object_key: string;
  job_id: string;
}

interface ExportResponse {
  export_id: string;
  deck_id: string;
  format: string;
  download_url: string;
  card_count: number;
}

/**
 * Typed wrapper around the slide2anki HTTP API.
 */
class ApiClient {
  private baseUrl: string;

  /**
   * Create a new API client with a base URL.
   */
  constructor(baseUrl: string = resolveApiBase()) {
    this.baseUrl = baseUrl;
  }

  /**
   * Perform a JSON request against the API.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Check the API health endpoint.
   */
  async health(): Promise<{ status: string }> {
    return this.request('/api/v1/health');
  }

  /**
   * List all projects.
   */
  async listProjects(): Promise<Project[]> {
    const data = await this.request<ProjectListResponse>('/api/v1/projects');
    return data.projects;
  }

  /**
   * Create a new project.
   */
  async createProject(name: string): Promise<Project> {
    return this.request('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  /**
   * Fetch project details by ID.
   */
  async getProject(projectId: string): Promise<Project> {
    return this.request(`/api/v1/projects/${projectId}`);
  }

  /**
   * List documents for a project.
   */
  async listDocuments(projectId: string): Promise<Document[]> {
    const data = await this.request<DocumentListResponse>(
      `/api/v1/projects/${projectId}/documents`
    );
    return data.documents;
  }

  /**
   * Upload a document to a project.
   */
  async uploadDocument(
    projectId: string,
    file: File
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${this.baseUrl}/api/v1/projects/${projectId}/documents`,
      {
        method: 'POST',
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  /**
   * List chapters for a project.
   */
  async listChapters(projectId: string): Promise<Chapter[]> {
    const data = await this.request<ChapterListResponse>(
      `/api/v1/projects/${projectId}/chapters`
    );
    return data.chapters;
  }

  /**
   * Fetch the latest markdown for a project.
   */
  async getMarkdown(projectId: string): Promise<MarkdownVersion> {
    return this.request(`/api/v1/projects/${projectId}/markdown`);
  }

  /**
   * List markdown blocks for a project.
   */
  async listMarkdownBlocks(
    projectId: string,
    chapterId?: string
  ): Promise<MarkdownBlock[]> {
    const params = chapterId ? `?chapter_id=${chapterId}` : '';
    return this.request(`/api/v1/projects/${projectId}/blocks${params}`);
  }

  /**
   * Update a markdown block.
   */
  async updateMarkdownBlock(
    blockId: string,
    content: string
  ): Promise<MarkdownBlock> {
    return this.request(`/api/v1/blocks/${blockId}`, {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    });
  }

  /**
   * Generate decks for a set of chapters.
   */
  async generateDecks(
    projectId: string,
    chapterIds: string[],
    maxCards: number,
    focus: Record<string, boolean> | null,
    customInstructions: string | null
  ): Promise<Deck[]> {
    const data = await this.request<DeckListResponse>(
      `/api/v1/projects/${projectId}/decks/generate`,
      {
        method: 'POST',
        body: JSON.stringify({
          chapter_ids: chapterIds,
          max_cards: maxCards,
          focus,
          custom_instructions: customInstructions,
        }),
      }
    );
    return data.decks;
  }

  /**
   * List decks, optionally filtered by project.
   */
  async listDecks(projectId?: string): Promise<Deck[]> {
    const params = projectId ? `?project_id=${projectId}` : '';
    const data = await this.request<DeckListResponse>(`/api/v1/decks${params}`);
    return data.decks;
  }

  /**
   * Fetch a single deck by ID.
   */
  async getDeck(deckId: string): Promise<Deck> {
    return this.request(`/api/v1/decks/${deckId}`);
  }

  /**
   * List jobs, optionally filtered by project.
   */
  async listJobs(projectId?: string): Promise<Job[]> {
    const params = projectId ? `?project_id=${projectId}` : '';
    const data = await this.request<JobListResponse>(`/api/v1/jobs${params}`);
    return data.jobs;
  }

  /**
   * Fetch a single job by ID.
   */
  async getJob(jobId: string): Promise<Job> {
    return this.request(`/api/v1/jobs/${jobId}`);
  }

  /**
   * List the most recent events for a job (chronological order).
   */
  async listJobEvents(jobId: string, limit: number = 200): Promise<JobEvent[]> {
    const data = await this.request<JobEventListResponse>(
      `/api/v1/jobs/${jobId}/events?limit=${limit}`
    );
    return data.events;
  }

  /**
   * Cancel a job if it is pending or running.
   */
  async cancelJob(jobId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/jobs/${jobId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to cancel job: ${response.status}`);
    }
  }

  /**
   * Retry a failed or cancelled job.
   * If the job has checkpoint data, it will resume from the last checkpoint.
   */
  async retryJob(jobId: string): Promise<Job> {
    return this.request(`/api/v1/jobs/${jobId}/retry`, {
      method: 'POST',
    });
  }

  /**
   * List card drafts for a deck.
   */
  async listCards(deckId: string): Promise<CardDraft[]> {
    const data = await this.request<CardDraftListResponse>(
      `/api/v1/decks/${deckId}/cards`
    );
    return data.cards;
  }

  /**
   * Update a card draft.
   */
  async updateCard(
    cardId: string,
    updates: Partial<CardDraft>
  ): Promise<CardDraft> {
    return this.request(`/api/v1/cards/${cardId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  /**
   * List revisions for a card draft.
   */
  async listCardRevisions(cardId: string): Promise<CardRevision[]> {
    const data = await this.request<CardRevisionListResponse>(
      `/api/v1/cards/${cardId}/revisions`
    );
    return data.revisions;
  }

  /**
   * List slides for a project, including signed URLs when available.
   */
  async listSlides(projectId: string): Promise<Slide[]> {
    const data = await this.request<SlideListResponse>(
      `/api/v1/projects/${projectId}/slides`
    );
    return data.slides;
  }

  /**
   * Trigger an export and return the download URL endpoint.
   */
  async exportDeck(
    deckId: string,
    format: 'tsv' | 'apkg',
    includeRejected = false
  ): Promise<ExportResponse> {
    return this.request(`/api/v1/decks/${deckId}/export`, {
      method: 'POST',
      body: JSON.stringify({ format, include_rejected: includeRejected }),
    });
  }

  /**
   * Resolve a signed download URL for an export.
   */
  async getExportDownloadUrl(exportId: string): Promise<string> {
    const data = await this.request<{ download_url: string }>(
      `/api/v1/exports/${exportId}/download`
    );
    return data.download_url;
  }

  /**
   * Fetch persisted app settings (API keys are masked).
   */
  async getSettings(): Promise<AppSettings> {
    return this.request<AppSettings>(`/api/v1/settings`);
  }

  /**
   * Persist app settings. `api_key` is optional and write-only.
   */
  async updateSettings(payload: AppSettingsUpdate): Promise<AppSettings> {
    return this.request<AppSettings>(`/api/v1/settings`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }
}

export const api = new ApiClient();
