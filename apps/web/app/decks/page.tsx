'use client';

import { useState } from 'react';
import { FolderOpen, FileText, MoreVertical, Download, Trash2 } from 'lucide-react';

interface Deck {
  id: string;
  name: string;
  card_count: number;
  pending_review: number;
  status: 'processing' | 'ready' | 'exported';
  created_at: string;
}

// Mock data for demo
const mockDecks: Deck[] = [
  {
    id: 'd1',
    name: 'Biology 101 - Cell Structure',
    card_count: 45,
    pending_review: 12,
    status: 'ready',
    created_at: new Date().toISOString(),
  },
  {
    id: 'd2',
    name: 'History - World War II',
    card_count: 78,
    pending_review: 0,
    status: 'exported',
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: 'd3',
    name: 'Chemistry - Organic Compounds',
    card_count: 0,
    pending_review: 0,
    status: 'processing',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
];

export default function DecksPage() {
  const [decks] = useState<Deck[]>(mockDecks);

  const getStatusBadge = (status: Deck['status']) => {
    const styles = {
      processing: 'bg-yellow-100 text-yellow-700',
      ready: 'bg-green-100 text-green-700',
      exported: 'bg-gray-100 text-gray-700',
    };
    const labels = {
      processing: 'Processing',
      ready: 'Ready for Review',
      exported: 'Exported',
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">My Decks</h1>
        <a
          href="/"
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          New Upload
        </a>
      </div>

      {decks.length === 0 ? (
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
                  {getStatusBadge(deck.status)}
                </div>

                <div className="text-sm text-gray-600 space-y-1">
                  <div>{deck.card_count} cards</div>
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
                    href={`/review/${deck.id}`}
                    className="flex-1 px-3 py-1.5 text-sm text-center bg-primary-600 text-white rounded hover:bg-primary-700"
                  >
                    Review
                  </a>
                )}
                {deck.status !== 'processing' && (
                  <button className="px-3 py-1.5 text-sm border rounded hover:bg-gray-100 flex items-center gap-1">
                    <Download className="w-4 h-4" />
                    Export
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
