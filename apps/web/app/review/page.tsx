/**
 * Review route wrapper.
 *
 * The underlying review UI is client-only because it depends on URL search params,
 * browser interactions, and optimistic UI updates. This wrapper provides the suspense
 * boundary required during `next build`.
 */

import { Suspense } from 'react';

import ReviewClient from './ReviewClient';

export default function ReviewPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto px-4 py-12 text-sm text-gray-500">
          Loading review…
        </div>
      }
    >
      <ReviewClient />
    </Suspense>
  );
}

