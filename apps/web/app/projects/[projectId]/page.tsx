/**
 * Project detail view for markdown and deck generation.
 */
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Layers,
  Loader2,
  UploadCloud,
  XCircle,
} from 'lucide-react';

import {
  api,
  Chapter,
  Document,
  Job,
  MarkdownBlock,
  MarkdownVersion,
  Project,
} from '@/lib/api';

interface FocusOption {
  key: string;
  label: string;
}

const focusOptions: FocusOption[] = [
  { key: 'definitions', label: 'Definitions' },
  { key: 'facts', label: 'Facts' },
  { key: 'processes', label: 'Processes' },
  { key: 'relationships', label: 'Relationships' },
  { key: 'formulas', label: 'Formulas' },
];

/**
 * Map job status to display properties (icon, color, label).
 */
function getJobStatusDisplay(status: Job['status']) {
  switch (status) {
    case 'pending':
      return {
        icon: Clock,
        colorClass: 'text-gray-500',
        bgClass: 'bg-gray-100',
        label: 'Pending',
      };
    case 'running':
      return {
        icon: Loader2,
        colorClass: 'text-blue-600',
        bgClass: 'bg-blue-50',
        label: 'Running',
        animate: true,
      };
    case 'completed':
      return {
        icon: CheckCircle,
        colorClass: 'text-green-600',
        bgClass: 'bg-green-50',
        label: 'Completed',
      };
    case 'failed':
      return {
        icon: XCircle,
        colorClass: 'text-red-600',
        bgClass: 'bg-red-50',
        label: 'Failed',
      };
    case 'cancelled':
      return {
        icon: AlertCircle,
        colorClass: 'text-yellow-600',
        bgClass: 'bg-yellow-50',
        label: 'Cancelled',
      };
    default:
      return {
        icon: Clock,
        colorClass: 'text-gray-500',
        bgClass: 'bg-gray-100',
        label: status,
      };
  }
}

/**
 * Format job type for display.
 */
function formatJobType(jobType: string): string {
  switch (jobType) {
    case 'markdown_build':
      return 'Building Markdown';
    case 'deck_generation':
      return 'Generating Cards';
    case 'export':
      return 'Exporting Deck';
    default:
      return jobType;
  }
}

/**
 * Render project details including markdown and generation controls.
 */
export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.projectId as string | undefined;

  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [blocks, setBlocks] = useState<MarkdownBlock[]>([]);
  const [markdown, setMarkdown] = useState<MarkdownVersion | null>(null);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [maxCards, setMaxCards] = useState(0);
  const [customInstructions, setCustomInstructions] = useState('');
  const [focus, setFocus] = useState<Record<string, boolean>>({});
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /**
   * Automatically clear transient errors so users can continue without reloading.
   */
  useEffect(() => {
    if (!errorMessage) {
      return undefined;
    }

    const timer = setTimeout(() => setErrorMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [errorMessage]);

  /**
   * Load project data, documents, chapters, blocks, and markdown snapshot.
   */
  const loadProject = useCallback(async () => {
    if (!projectId) {
      setErrorMessage('Missing project ID.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [projectData, docs, chapterList, blockList, markdownVersion, jobList] =
        await Promise.all([
          api.getProject(projectId),
          api.listDocuments(projectId),
          api.listChapters(projectId),
          api.listMarkdownBlocks(projectId),
          api.getMarkdown(projectId),
          api.listJobs(projectId),
        ]);
      setProject(projectData);
      setDocuments(docs);
      setChapters(chapterList);
      setBlocks(blockList);
      setMarkdown(markdownVersion);
      setJobs(jobList);
      setSelectedChapters(chapterList.map((chapter) => chapter.id));
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load project';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  /**
   * Identify jobs that are still in progress (pending or running).
   */
  const activeJobs = useMemo(
    () => jobs.filter((job) => job.status === 'pending' || job.status === 'running'),
    [jobs]
  );

  /**
   * Poll for job updates when there are active jobs.
   * Also refresh project data when a job completes to pick up new chapters/blocks.
   */
  useEffect(() => {
    if (activeJobs.length === 0 || !projectId) {
      return undefined;
    }

    const interval = setInterval(async () => {
      try {
        const updatedJobs = await api.listJobs(projectId);
        const previousActiveIds = new Set(activeJobs.map((j) => j.id));
        const newlyCompleted = updatedJobs.filter(
          (j) =>
            previousActiveIds.has(j.id) &&
            (j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled')
        );

        setJobs(updatedJobs);

        // Refresh project data if any job just completed (new chapters/blocks may exist)
        if (newlyCompleted.length > 0) {
          const [chapterList, blockList, markdownVersion] = await Promise.all([
            api.listChapters(projectId),
            api.listMarkdownBlocks(projectId),
            api.getMarkdown(projectId),
          ]);
          setChapters(chapterList);
          setBlocks(blockList);
          setMarkdown(markdownVersion);
          setSelectedChapters(chapterList.map((chapter) => chapter.id));
        }
      } catch {
        // Silently ignore polling errors to avoid UI disruption
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [activeJobs, projectId]);

  /**
   * Group blocks by chapter for display.
   */
  const blocksByChapter = useMemo(() => {
    const map = new Map<string, MarkdownBlock[]>();
    blocks.forEach((block) => {
      const chapterBlocks = map.get(block.chapter_id) || [];
      chapterBlocks.push(block);
      map.set(block.chapter_id, chapterBlocks);
    });
    return map;
  }, [blocks]);

  /**
   * Upload additional documents to the project.
   */
  const handleUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files || []);
      if (!projectId || !files.length) {
        return;
      }
      setErrorMessage(null);
      try {
        for (const file of files) {
          await api.uploadDocument(projectId, file);
        }
        await loadProject();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Upload failed';
        setErrorMessage(message);
      }
    },
    [projectId, loadProject]
  );

  /**
   * Toggle a chapter selection for deck generation.
   */
  const toggleChapter = useCallback(
    (chapterId: string) => {
      setSelectedChapters((current) =>
        current.includes(chapterId)
          ? current.filter((id) => id !== chapterId)
          : [...current, chapterId]
      );
    },
    []
  );

  /**
   * Toggle a focus option for deck generation.
   */
  const toggleFocus = useCallback((key: string) => {
    setFocus((current) => ({
      ...current,
      [key]: !current[key],
    }));
  }, []);

  /**
   * Save a markdown block edit.
   */
  const saveBlockEdit = useCallback(async () => {
    if (!editingBlockId) {
      return;
    }
    setErrorMessage(null);
    try {
      await api.updateMarkdownBlock(editingBlockId, editedContent);
      setEditingBlockId(null);
      setEditedContent('');
      await loadProject();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to update block';
      setErrorMessage(message);
    }
  }, [editedContent, editingBlockId, loadProject]);

  /**
   * Generate decks for the selected chapters.
   */
  const handleGenerate = useCallback(async () => {
    if (!projectId || selectedChapters.length === 0) {
      setErrorMessage('Select at least one chapter.');
      return;
    }
    setErrorMessage(null);
    try {
      await api.generateDecks(
        projectId,
        selectedChapters,
        maxCards,
        focus,
        customInstructions || null
      );
      router.push(`/decks?projectId=${projectId}`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Deck generation failed';
      setErrorMessage(message);
    }
  }, [customInstructions, focus, maxCards, projectId, router, selectedChapters]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-12 text-center text-gray-500">
        Loading project...
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="container mx-auto px-4 py-12 text-center text-red-600">
        {errorMessage}
      </div>
    );
  }

  if (!project) {
    return (
      <div className="container mx-auto px-4 py-12 text-center text-gray-500">
        Project not found.
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          <p className="text-sm text-gray-500">
            {documents.length} documents · {chapters.length} chapters
          </p>
        </div>
        <label className="inline-flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50 cursor-pointer">
          <UploadCloud className="w-4 h-4" />
          Upload documents
          <input
            type="file"
            multiple
            accept="application/pdf"
            className="hidden"
            onChange={handleUpload}
          />
        </label>
      </div>

      {/* Active Jobs Section - shows when there are running or pending jobs */}
      {activeJobs.length > 0 && (
        <section className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
            <h2 className="text-sm font-semibold text-blue-900">
              Processing in Background
            </h2>
          </div>
          <div className="space-y-2">
            {activeJobs.map((job) => {
              const statusDisplay = getJobStatusDisplay(job.status);
              const StatusIcon = statusDisplay.icon;
              return (
                <div
                  key={job.id}
                  className="bg-white rounded-lg p-3 border border-blue-100"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <StatusIcon
                        className={`w-4 h-4 ${statusDisplay.colorClass} ${
                          'animate' in statusDisplay && statusDisplay.animate
                            ? 'animate-spin'
                            : ''
                        }`}
                      />
                      <span className="text-sm font-medium text-gray-900">
                        {formatJobType(job.job_type)}
                      </span>
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${statusDisplay.bgClass} ${statusDisplay.colorClass}`}
                    >
                      {statusDisplay.label}
                    </span>
                  </div>
                  {job.current_step && (
                    <p className="text-xs text-gray-600 mb-2">{job.current_step}</p>
                  )}
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1 text-right">
                    {job.progress}%
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Recent Job Results - shows completed/failed jobs from this session */}
      {jobs.filter(
        (job) =>
          (job.status === 'completed' || job.status === 'failed') &&
          new Date(job.created_at).getTime() > Date.now() - 1000 * 60 * 30
      ).length > 0 && (
        <section className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Recent Jobs</h2>
          <div className="space-y-2">
            {jobs
              .filter(
                (job) =>
                  (job.status === 'completed' || job.status === 'failed') &&
                  new Date(job.created_at).getTime() > Date.now() - 1000 * 60 * 30
              )
              .slice(0, 5)
              .map((job) => {
                const statusDisplay = getJobStatusDisplay(job.status);
                const StatusIcon = statusDisplay.icon;
                return (
                  <div
                    key={job.id}
                    className={`flex items-center justify-between p-2 rounded-lg ${statusDisplay.bgClass}`}
                  >
                    <div className="flex items-center gap-2">
                      <StatusIcon className={`w-4 h-4 ${statusDisplay.colorClass}`} />
                      <span className="text-sm text-gray-700">
                        {formatJobType(job.job_type)}
                      </span>
                    </div>
                    <span className={`text-xs ${statusDisplay.colorClass}`}>
                      {statusDisplay.label}
                    </span>
                  </div>
                );
              })}
          </div>
        </section>
      )}

      <section className="bg-white border rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Chapters</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {chapters.map((chapter) => (
            <label
              key={chapter.id}
              className="flex items-center gap-3 p-3 border rounded-lg"
            >
              <input
                type="checkbox"
                checked={selectedChapters.includes(chapter.id)}
                onChange={() => toggleChapter(chapter.id)}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm text-gray-700">{chapter.title}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="bg-white border rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">
            Generate Decks
          </h2>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max cards per chapter (0 = unlimited)
            </label>
            <input
              type="number"
              min={0}
              value={maxCards}
              onChange={(event) => setMaxCards(Number(event.target.value))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Focus areas
            </label>
            <div className="flex flex-wrap gap-2">
              {focusOptions.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  onClick={() => toggleFocus(option.key)}
                  className={`px-3 py-1.5 rounded-full text-sm border ${
                    focus[option.key]
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white text-gray-600'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Custom instructions
          </label>
          <textarea
            value={customInstructions}
            onChange={(event) => setCustomInstructions(event.target.value)}
            rows={3}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="Focus on formulas and keep prompts short."
          />
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Generate Decks
        </button>
      </section>

      <section className="bg-white border rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">
            Markdown Blocks
          </h2>
        </div>
        {chapters.map((chapter) => (
          <div key={chapter.id} className="border rounded-lg p-4 space-y-3">
            <h3 className="font-medium text-gray-900">{chapter.title}</h3>
            {(blocksByChapter.get(chapter.id) || []).map((block) => (
              <div key={block.id} className="border rounded-lg p-3">
                {editingBlockId === block.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editedContent}
                      onChange={(event) => setEditedContent(event.target.value)}
                      rows={4}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={saveBlockEdit}
                        className="px-3 py-1.5 bg-primary-600 text-white rounded-lg"
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingBlockId(null);
                          setEditedContent('');
                        }}
                        className="px-3 py-1.5 border rounded-lg"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-4">
                    <div className="text-sm text-gray-700 whitespace-pre-wrap">
                      {block.content}
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingBlockId(block.id);
                        setEditedContent(block.content);
                      }}
                      className="text-sm text-primary-600 hover:text-primary-700"
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </section>

      <section className="bg-white border rounded-lg p-6 space-y-2">
        <h2 className="text-lg font-semibold text-gray-900">
          Markdown Preview
        </h2>
        <pre className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded-lg max-h-96 overflow-auto">
          {markdown?.content || 'No markdown generated yet.'}
        </pre>
      </section>
    </div>
  );
}
