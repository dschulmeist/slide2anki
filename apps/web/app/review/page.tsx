/**
 * Review page for approving and editing generated cards.
 */
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Check, X, Flag } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

import { api, CardDraft, Deck, Slide } from '@/lib/api';

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
export default function ReviewPage() {
  const searchParams = useSearchParams();
  const deckId = searchParams.get('deckId');
  const [cards, setCards] = useState<CardDraft[]>([]);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [deck, setDeck] = useState<Deck | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
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
   * Update card status locally and persist to the API.
   */
  const updateCardStatus = useCallback(
    async (status: 'approved' | 'rejected') => {
      if (!currentCard) {
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

      const nextPending = cards.findIndex(
        (card, i) => i > currentIndex && card.status === 'pending'
      );
      if (nextPending !== -1) {
        setCurrentIndex(nextPending);
      } else if (currentIndex < cards.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    },
    [cards, currentCard, currentIndex]
  );

  const pendingCount = cards.filter(c => c.status === 'pending').length;
  const approvedCount = cards.filter(c => c.status === 'approved').length;
  const rejectedCount = cards.filter(c => c.status === 'rejected').length;

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-12 text-center text-gray-500">
        Loading review data...
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

  if (!currentCard) {
    return (
      <div className="container mx-auto px-4 py-12 text-center">
        <h2 className="text-xl font-semibold mb-4">No cards to review</h2>
        <a href="/decks" className="text-primary-600 hover:underline">
          Back to decks
        </a>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col">
      {/* Progress bar */}
      <div className="bg-white border-b px-4 py-3">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <a href="/decks" className="text-gray-500 hover:text-gray-700">
              <ChevronLeft className="w-5 h-5" />
            </a>
            <span className="font-medium">Review Cards</span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-gray-500">{pendingCount} pending</span>
            <span className="text-green-600">{approvedCount} approved</span>
            <span className="text-red-600">{rejectedCount} rejected</span>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Left: Slide image */}
        <div className="w-1/2 bg-gray-100 p-4 flex items-center justify-center relative">
          <div className="relative max-w-full max-h-full">
            {currentSlide?.image_url ? (
              <img
                src={currentSlide.image_url}
                alt={`Slide ${currentSlide.page_index + 1}`}
                className="max-w-full max-h-[450px] rounded"
              />
            ) : (
              <div className="bg-gray-300 w-[600px] h-[450px] rounded flex items-center justify-center text-gray-500">
                Slide preview unavailable
              </div>
            )}
            {/* Evidence highlight overlay would go here */}
            {evidenceBox && (
              <div
                className="absolute border-2 border-yellow-400 bg-yellow-200 bg-opacity-30 pointer-events-none"
                style={{
                  left: `${evidenceBox.x * 100}%`,
                  top: `${evidenceBox.y * 100}%`,
                  width: `${evidenceBox.width * 100}%`,
                  height: `${evidenceBox.height * 100}%`,
                }}
              />
            )}
          </div>
        </div>

        {/* Right: Card editor */}
        <div className="w-1/2 bg-white p-6 flex flex-col">
          {/* Card navigation */}
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
              disabled={currentIndex === 0}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm text-gray-500">
              Card {currentIndex + 1} of {cards.length}
            </span>
            <button
              onClick={() =>
                setCurrentIndex(Math.min(cards.length - 1, currentIndex + 1))
              }
              disabled={currentIndex === cards.length - 1}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {/* Card content */}
          <div className="flex-1 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Front
              </label>
              <div className="p-3 bg-gray-50 rounded-lg border">
                {currentCard.front}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Back
              </label>
              <div className="p-3 bg-gray-50 rounded-lg border whitespace-pre-wrap">
                {currentCard.back}
              </div>
            </div>

            {/* Metadata */}
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-500">
                Confidence: {Math.round(currentCard.confidence * 100)}%
              </span>
              {getFlags(currentCard).length > 0 && (
                <span className="flex items-center gap-1 text-yellow-600">
                  <Flag className="w-4 h-4" />
                  {getFlags(currentCard).join(', ')}
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t">
            <button
              onClick={() => updateCardStatus('rejected')}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
            >
              <X className="w-5 h-5" />
              Reject
            </button>
            <button
              onClick={() => updateCardStatus('approved')}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <Check className="w-5 h-5" />
              Approve
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
