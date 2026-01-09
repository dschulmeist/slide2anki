'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Check, X, Edit, Flag } from 'lucide-react';

interface Card {
  id: string;
  front: string;
  back: string;
  confidence: number;
  flags: string[];
  status: 'pending' | 'approved' | 'rejected';
  slide_index: number;
  evidence_bbox: { x: number; y: number; width: number; height: number } | null;
}

interface Slide {
  index: number;
  image_url: string;
}

// Mock data for demo
const mockCards: Card[] = [
  {
    id: 'c1',
    front: 'What is the primary function of mitochondria?',
    back: 'To produce ATP (adenosine triphosphate) through cellular respiration, serving as the "powerhouse" of the cell.',
    confidence: 0.92,
    flags: [],
    status: 'pending',
    slide_index: 0,
    evidence_bbox: { x: 100, y: 150, width: 400, height: 200 },
  },
  {
    id: 'c2',
    front: 'What are the two main stages of cellular respiration?',
    back: '1. Glycolysis (in cytoplasm)\n2. Oxidative phosphorylation (in mitochondria)',
    confidence: 0.85,
    flags: ['may_need_context'],
    status: 'pending',
    slide_index: 0,
    evidence_bbox: { x: 100, y: 400, width: 400, height: 150 },
  },
  {
    id: 'c3',
    front: 'What is the role of the inner mitochondrial membrane?',
    back: 'Contains the electron transport chain and ATP synthase, which are essential for oxidative phosphorylation.',
    confidence: 0.78,
    flags: [],
    status: 'pending',
    slide_index: 1,
    evidence_bbox: null,
  },
];

const mockSlides: Slide[] = [
  { index: 0, image_url: '/api/placeholder/800/600' },
  { index: 1, image_url: '/api/placeholder/800/600' },
];

export default function ReviewPage() {
  const [cards, setCards] = useState<Card[]>(mockCards);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [editedCard, setEditedCard] = useState<Card | null>(null);

  const currentCard = cards[currentIndex];
  const currentSlide = mockSlides.find(s => s.index === currentCard?.slide_index);

  const updateCardStatus = (status: 'approved' | 'rejected') => {
    setCards(prev =>
      prev.map((card, i) =>
        i === currentIndex ? { ...card, status } : card
      )
    );
    // Auto-advance to next pending card
    const nextPending = cards.findIndex((c, i) => i > currentIndex && c.status === 'pending');
    if (nextPending !== -1) {
      setCurrentIndex(nextPending);
    } else if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const pendingCount = cards.filter(c => c.status === 'pending').length;
  const approvedCount = cards.filter(c => c.status === 'approved').length;
  const rejectedCount = cards.filter(c => c.status === 'rejected').length;

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
            <div className="bg-gray-300 w-[600px] h-[450px] rounded flex items-center justify-center text-gray-500">
              Slide {currentCard.slide_index + 1} Preview
            </div>
            {/* Evidence highlight overlay would go here */}
            {currentCard.evidence_bbox && (
              <div
                className="absolute border-2 border-yellow-400 bg-yellow-200 bg-opacity-30 pointer-events-none"
                style={{
                  left: currentCard.evidence_bbox.x * 0.75,
                  top: currentCard.evidence_bbox.y * 0.75,
                  width: currentCard.evidence_bbox.width * 0.75,
                  height: currentCard.evidence_bbox.height * 0.75,
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
              onClick={() => setCurrentIndex(Math.min(cards.length - 1, currentIndex + 1))}
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
              {currentCard.flags.length > 0 && (
                <span className="flex items-center gap-1 text-yellow-600">
                  <Flag className="w-4 h-4" />
                  {currentCard.flags.join(', ')}
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
              onClick={() => setIsEditing(true)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              <Edit className="w-5 h-5" />
              Edit
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
