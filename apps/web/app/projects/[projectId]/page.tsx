/**
 * Project detail view for markdown and deck generation.
 */
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { CheckCircle, FileText, Layers, UploadCloud } from 'lucide-react';

import {
  api,
  Chapter,
  Document,
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
      const [projectData, docs, chapterList, blockList, markdownVersion] =
        await Promise.all([
          api.getProject(projectId),
          api.listDocuments(projectId),
          api.listChapters(projectId),
          api.listMarkdownBlocks(projectId),
          api.getMarkdown(projectId),
        ]);
      setProject(projectData);
      setDocuments(docs);
      setChapters(chapterList);
      setBlocks(blockList);
      setMarkdown(markdownVersion);
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
