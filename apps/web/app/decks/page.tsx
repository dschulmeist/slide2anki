/**
 * Deck list page with export actions.
 */
'use client';

import { useCallback, useEffect, useState } from 'react';
import { FolderOpen, FileText, MoreVertical, Download } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

import { api, Deck } from '@/lib/api';

type DeckStatus = 'processing' | 'ready' | 'exported' | 'created';

/**
 * Render the decks page with export actions.
 */
export default function DecksPage() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('projectId') || undefined;
  const [decks, setDecks] = useState<Deck[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exportingDeckId, setExportingDeckId] = useState<string | null>(null);

  /**
   * Load decks from the API.
   */
  const loadDecks = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const deckList = await api.listDecks(projectId);
      setDecks(deckList);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load decks';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadDecks();
  }, [loadDecks]);

  /**
   * Trigger an export for a deck and open the download URL.
   */
  const handleExport = useCallback(async (deckId: string) => {
    setExportingDeckId(deckId);
    setErrorMessage(null);
    try {
      const exportJob = await api.exportDeck(deckId, 'tsv');
      const downloadUrl = await api.getExportDownloadUrl(
        exportJob.export_id
      );
      window.open(downloadUrl, '_blank', 'noopener,noreferrer');
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Export failed';
      setErrorMessage(message);
    } finally {
      setExportingDeckId(null);
    }
  }, []);

  /**
   * Render a status badge for a deck.
   */
  const getStatusBadge = (status: DeckStatus) => {
    const styles: Record<DeckStatus, string> = {
      processing: 'bg-yellow-100 text-yellow-700',
      ready: 'bg-green-100 text-green-700',
      exported: 'bg-gray-100 text-gray-700',
      created: 'bg-gray-100 text-gray-700',
    };
    const labels: Record<DeckStatus, string> = {
      processing: 'Processing',
      ready: 'Ready for Review',
      exported: 'Exported',
      created: 'Ready for Review',
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  /**
   * Normalize deck status for display.
   */
  const normalizeStatus = (status: Deck['status']): DeckStatus => {
    if (status === 'processing' || status === 'ready' || status === 'exported') {
      return status;
    }
    return 'created';
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">My Decks</h1>
        <a
          href="/projects"
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          View Projects
        </a>
      </div>

      {errorMessage ? (
        <div className="bg-white rounded-lg border p-12 text-center text-red-600">
          {errorMessage}
        </div>
      ) : isLoading ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-500">
          Loading decks...
        </div>
      ) : decks.length === 0 ? (
        <div className="bg-white rounded-lg border p-12 text-center">
          <FolderOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No decks yet</h3>
          <p className="text-gray-500 mb-4">
            Upload a PDF to create your first deck
          </p>
          <a
            href="/"
            className="inline-block px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Upload PDF
          </a>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {decks.map((deck) => (
            <div
              key={deck.id}
              className="bg-white rounded-lg border hover:shadow-md transition-shadow"
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary-500" />
                    <h3 className="font-medium text-gray-900 line-clamp-1">
                      {deck.name}
                    </h3>
                  </div>
                  <button className="p-1 hover:bg-gray-100 rounded">
                    <MoreVertical className="w-4 h-4 text-gray-400" />
                  </button>
                </div>

                <div className="flex items-center gap-2 mb-3">
                  {getStatusBadge(normalizeStatus(deck.status))}
                </div>

                <div className="text-sm text-gray-600 space-y-1">
                  <div>{deck.card_count || 0} cards</div>
                  {deck.pending_review > 0 && (
                    <div className="text-yellow-600">
                      {deck.pending_review} pending review
                    </div>
                  )}
                </div>
              </div>

              <div className="px-4 py-3 border-t bg-gray-50 flex gap-2">
                {deck.status === 'ready' && (
                  <a
                    href={`/review?deckId=${deck.id}`}
                    className="flex-1 px-3 py-1.5 text-sm text-center bg-primary-600 text-white rounded hover:bg-primary-700"
                  >
                    Review
                  </a>
                )}
                {deck.status !== 'processing' && (
                  <button
                    onClick={() => handleExport(deck.id)}
                    disabled={exportingDeckId === deck.id}
                    className="px-3 py-1.5 text-sm border rounded hover:bg-gray-100 flex items-center gap-1 disabled:opacity-50"
                  >
                    <Download className="w-4 h-4" />
                    {exportingDeckId === deck.id ? 'Exporting...' : 'Export'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
