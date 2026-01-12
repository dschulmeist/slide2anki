/**
 * Deck list route wrapper.
 *
 * Next.js pre-renders routes during `next build`. Client hooks like `useSearchParams`
 * require a suspense boundary, so we keep the page as a server component that wraps
 * the client implementation.
 */

import { Suspense } from 'react';

import DecksClient from './DecksClient';

export default function DecksPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto px-4 py-12 text-sm text-gray-500">
          Loading decks…
        </div>
      }
    >
      <DecksClient />
    </Suspense>
  );
}

