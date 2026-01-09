/**
 * Dashboard view for tracking background jobs.
 */
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

import { api, Deck, Job } from '@/lib/api';

interface JobWithDeck extends Job {
  deck_name: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Render the dashboard with job status updates.
 */
export default function DashboardPage() {
  const [jobs, setJobs] = useState<JobWithDeck[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const streamsRef = useRef<Map<string, EventSource>>(new Map());

  /**
   * Load jobs and map deck names for display.
   */
  const loadJobs = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [jobList, deckList] = await Promise.all([
        api.listJobs(),
        api.listDecks(),
      ]);
      const deckMap = new Map<string, Deck>(
        deckList.map((deck) => [deck.id, deck])
      );
      const hydratedJobs = jobList.map((job) => ({
        ...job,
        deck_name: deckMap.get(job.deck_id)?.name ?? 'Untitled deck',
      }));
      setJobs(hydratedJobs);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load jobs';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  /**
   * Keep streaming connections for running jobs only.
   */
  useEffect(() => {
    const activeJobIds = new Set(
      jobs.filter((job) => job.status === 'running').map((job) => job.id)
    );
    const streams = streamsRef.current;

    jobs.forEach((job) => {
      if (job.status !== 'running' || streams.has(job.id)) {
        return;
      }

      const source = new EventSource(
        `${API_BASE}/api/v1/jobs/${job.id}/stream`
      );
      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as {
            progress: number;
            step: string;
          };
          setJobs((current) =>
            current.map((item) =>
              item.id === job.id
                ? { ...item, progress: data.progress, current_step: data.step }
                : item
            )
          );
        } catch {
          return;
        }
      };
      source.onerror = () => {
        source.close();
        streams.delete(job.id);
      };
      streams.set(job.id, source);
    });

    for (const [jobId, source] of streams) {
      if (!activeJobIds.has(jobId)) {
        source.close();
        streams.delete(jobId);
      }
    }

    return () => {
      for (const source of streams.values()) {
        source.close();
      }
      streams.clear();
    };
  }, [jobs]);

  /**
   * Render a status icon for the current job.
   */
  const getStatusIcon = (status: Job['status']) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-400" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'cancelled':
        return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  /**
   * Render a status badge for the current job.
   */
  const getStatusBadge = (status: Job['status']) => {
    const styles = {
      pending: 'bg-gray-100 text-gray-700',
      running: 'bg-primary-100 text-primary-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
      cancelled: 'bg-gray-100 text-gray-700',
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <a
          href="/"
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          New Upload
        </a>
      </div>

      <div className="bg-white rounded-lg border">
        <div className="px-6 py-4 border-b">
          <h2 className="font-semibold text-gray-900">Recent Jobs</h2>
        </div>

        {errorMessage ? (
          <div className="px-6 py-12 text-center text-red-600">
            {errorMessage}
          </div>
        ) : isLoading ? (
          <div className="px-6 py-12 text-center text-gray-500">
            Loading jobs...
          </div>
        ) : jobs.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            No jobs yet. Upload a PDF to get started.
          </div>
        ) : (
          <div className="divide-y">
            {jobs.map((job) => (
              <div key={job.id} className="px-6 py-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(job.status)}
                    <span className="font-medium text-gray-900">
                      {job.deck_name}
                    </span>
                    {getStatusBadge(job.status)}
                  </div>
                  <a
                    href={`/review?deckId=${job.deck_id}`}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    Review Deck
                  </a>
                </div>

                {job.status === 'running' && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                      <span>{job.current_step || 'Working...'}</span>
                      <span>{job.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${job.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="mt-2 text-xs text-gray-400">
                  Started {new Date(job.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
