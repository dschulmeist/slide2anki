/**
 * Review page for approving and editing generated cards.
 *
 * This component is client-only because it depends on URL search params and interactive edits.
 */
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Check, X, Flag, FolderOpen } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

import { api, CardDraft, CardRevision, Deck, Slide } from '@/lib/api';

interface EvidenceBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Evidence metadata used to locate slides and render highlights.
 */
interface EvidenceMeta {
  documentId: string | null;
  slideIndex: number | null;
  bbox: EvidenceBox | null;
}

/**
 * Extract evidence metadata for slide lookup and highlighting.
 */
const getEvidenceMeta = (card: CardDraft): EvidenceMeta => {
  const evidence = card.evidence_json;
  if (!Array.isArray(evidence) || evidence.length === 0) {
    return { documentId: null, slideIndex: null, bbox: null };
  }
  const first = evidence[0] as {
    document_id?: string;
    slide_index?: number;
    bbox?: EvidenceBox;
  };
  return {
    documentId: first?.document_id ?? null,
    slideIndex:
      typeof first?.slide_index === 'number' ? first.slide_index : null,
    bbox: first?.bbox ?? null,
  };
};

/**
 * Normalize card flags for display.
 */
const getFlags = (card: CardDraft): string[] => {
  return Array.isArray(card.flags_json)
    ? card.flags_json.filter((flag): flag is string => typeof flag === 'string')
    : [];
};

/**
 * Render the review experience for a deck.
 */
export default function ReviewClient() {
  const searchParams = useSearchParams();
  const deckId = searchParams.get('deckId');
  const [cards, setCards] = useState<CardDraft[]>([]);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [deck, setDeck] = useState<Deck | null>(null);
  const [revisions, setRevisions] = useState<CardRevision[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [draftFront, setDraftFront] = useState('');
  const [draftBack, setDraftBack] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /**
   * Load cards and slides for the selected deck.
   */
  const loadReviewData = useCallback(async () => {
    if (!deckId) {
      setIsLoading(false);
      setErrorMessage('Missing deck ID.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const deckResponse = await api.getDeck(deckId);
      const [cardList, slideList] = await Promise.all([
        api.listCards(deckId),
        api.listSlides(deckResponse.project_id),
      ]);
      setCards(cardList);
      setSlides(slideList);
      setDeck(deckResponse);
      setCurrentIndex(0);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load review data';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, [deckId]);

  /**
   * Load revision history for a card draft.
   */
  const loadRevisions = useCallback(async (cardId: string) => {
    try {
      const history = await api.listCardRevisions(cardId);
      setRevisions(history);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load revisions';
      setErrorMessage(message);
    }
  }, []);

  useEffect(() => {
    loadReviewData();
  }, [loadReviewData]);

  const currentCard = cards[currentIndex];
  const evidenceMeta = currentCard ? getEvidenceMeta(currentCard) : null;
  const evidenceBox = evidenceMeta?.bbox ?? null;
  const currentSlide = useMemo(() => {
    if (!evidenceMeta?.documentId || evidenceMeta.slideIndex === null) {
      return null;
    }
    return (
      slides.find(
        (slide) =>
          slide.document_id === evidenceMeta.documentId &&
          slide.page_index === evidenceMeta.slideIndex
      ) || null
    );
  }, [evidenceMeta, slides]);

  /**
   * Sync local edit state and revisions when the current card changes.
   */
  useEffect(() => {
    if (!currentCard) {
      setRevisions([]);
      return;
    }
    setDraftFront(currentCard.front);
    setDraftBack(currentCard.back);
    setIsEditing(false);
    loadRevisions(currentCard.id);
  }, [currentCard, loadRevisions]);

  /**
   * Update card status locally and persist to the API.
   */
  const updateCardStatus = useCallback(
    async (status: 'approved' | 'rejected') => {
      if (!currentCard || isEditing || isSaving) {
        return;
      }
      const updated = { status };

      setCards((prev) =>
        prev.map((card, i) =>
          i === currentIndex ? { ...card, ...updated } : card
        )
      );

      try {
        await api.updateCard(currentCard.id, updated);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to update card';
        setErrorMessage(message);
      }
    },
    [currentCard, currentIndex, isEditing, isSaving]
  );

  /**
   * Begin editing the current card.
   */
  const startEditing = useCallback(() => {
    if (!currentCard) {
      return;
    }
    setIsEditing(true);
    setDraftFront(currentCard.front);
    setDraftBack(currentCard.back);
  }, [currentCard]);

  /**
   * Cancel editing and reset the draft state.
   */
  const cancelEditing = useCallback(() => {
    if (!currentCard) {
      return;
    }
    setIsEditing(false);
    setDraftFront(currentCard.front);
    setDraftBack(currentCard.back);
  }, [currentCard]);

  /**
   * Save edited card content and refresh the revision list.
   */
  const saveEdits = useCallback(async () => {
    if (!currentCard) {
      return;
    }
    setIsSaving(true);
    setErrorMessage(null);
    try {
      await api.updateCard(currentCard.id, {
        front: draftFront,
        back: draftBack,
      });
      setCards((prev) =>
        prev.map((card, i) =>
          i === currentIndex
            ? { ...card, front: draftFront, back: draftBack }
            : card
        )
      );
      setIsEditing(false);
      await loadRevisions(currentCard.id);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to save edits';
      setErrorMessage(message);
    } finally {
      setIsSaving(false);
    }
  }, [currentCard, currentIndex, draftBack, draftFront, loadRevisions]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading review...</div>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto bg-white rounded-lg border p-8 text-center">
          <div className="text-red-600 mb-4">{errorMessage}</div>
          <a
            href="/dashboard"
            className="text-primary-600 hover:text-primary-700"
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    );
  }

  if (!deck || !currentCard) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto bg-white rounded-lg border p-8 text-center">
          <FolderOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No cards to review
          </h3>
          <p className="text-gray-500 mb-4">
            This deck does not have any cards yet
          </p>
          <a
            href="/dashboard"
            className="inline-block px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    );
  }

  const flags = getFlags(currentCard);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{deck.name}</h1>
            <p className="text-gray-500">
              Card {currentIndex + 1} of {cards.length}
            </p>
          </div>
          <a
            href={`/projects/${deck.project_id}`}
            className="text-primary-600 hover:text-primary-700"
          >
            Back to Project
          </a>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Slide Evidence */}
          <div className="bg-white rounded-lg border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Slide Evidence
            </h2>
            {currentSlide?.image_url ? (
              <div className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={currentSlide.image_url}
                  alt={`Slide ${evidenceMeta?.slideIndex ?? ''}`}
                  className="w-full rounded border"
                />
                {evidenceBox && (
                  <div
                    className="absolute border-2 border-red-500 bg-red-500/10"
                    style={{
                      left: `${evidenceBox.x * 100}%`,
                      top: `${evidenceBox.y * 100}%`,
                      width: `${evidenceBox.width * 100}%`,
                      height: `${evidenceBox.height * 100}%`,
                    }}
                  />
                )}
              </div>
            ) : (
              <div className="text-gray-500 text-center py-12">
                No slide evidence available
              </div>
            )}
          </div>

          {/* Card Review */}
          <div className="bg-white rounded-lg border p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Card</h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setCurrentIndex((idx) => Math.max(0, idx - 1))
                  }
                  disabled={currentIndex === 0}
                  className="p-2 border rounded disabled:opacity-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setCurrentIndex((idx) => Math.min(cards.length - 1, idx + 1))
                  }
                  disabled={currentIndex === cards.length - 1}
                  className="p-2 border rounded disabled:opacity-50"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-4 flex-1">
              {/* Editing Controls */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">
                  Status: {currentCard.status}
                </span>
                {isEditing ? (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={saveEdits}
                      disabled={isSaving}
                      className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEditing}
                      disabled={isSaving}
                      className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={startEditing}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    Edit
                  </button>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Front
                </label>
                {isEditing ? (
                  <textarea
                    value={draftFront}
                    onChange={(event) => setDraftFront(event.target.value)}
                    rows={3}
                    className="w-full p-3 bg-white rounded-lg border focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                ) : (
                  <div className="p-3 bg-gray-50 rounded-lg border">
                    {currentCard.front}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Back
                </label>
                {isEditing ? (
                  <textarea
                    value={draftBack}
                    onChange={(event) => setDraftBack(event.target.value)}
                    rows={4}
                    className="w-full p-3 bg-white rounded-lg border focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                ) : (
                  <div className="p-3 bg-gray-50 rounded-lg border whitespace-pre-wrap">
                    {currentCard.back}
                  </div>
                )}
              </div>

              {/* Metadata */}
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-500">
                  Confidence: {Math.round(currentCard.confidence * 100)}%
                </span>
                {flags.length > 0 && (
                  <span className="flex items-center gap-1 text-yellow-600">
                    <Flag className="w-4 h-4" />
                    {flags.join(', ')}
                  </span>
                )}
              </div>

              <div className="border-t pt-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Revision History
                </h3>
                {revisions.length === 0 ? (
                  <p className="text-xs text-gray-400">No revisions yet.</p>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-auto">
                    {revisions.map((revision) => (
                      <div
                        key={revision.id}
                        className="border rounded-lg p-2 text-xs text-gray-600"
                      >
                        <div className="flex items-center justify-between text-gray-400">
                          <span>Revision {revision.revision_number}</span>
                          <span>
                            {(revision.edited_by || 'system').toString()} -{' '}
                            {new Date(revision.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="mt-1 text-gray-600 whitespace-pre-wrap">
                          {revision.front}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-4 border-t">
              <button
                onClick={() => updateCardStatus('rejected')}
                disabled={isEditing || isSaving}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <X className="w-5 h-5" />
                Reject
              </button>
              <button
                onClick={() => updateCardStatus('approved')}
                disabled={isEditing || isSaving}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Check className="w-5 h-5" />
                Approve
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
