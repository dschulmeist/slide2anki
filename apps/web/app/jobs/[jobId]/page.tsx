/**
 * Job detail view that surfaces the latest progress and controls for a single job.
 */
'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, CheckCircle, Clock, Loader2 } from 'lucide-react';

import { api, Deck, Job, JobEvent, Project } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function JobDetailPage() {
  const params = useParams();
  const jobIdParam = params?.jobId ?? null;
  const jobId = Array.isArray(jobIdParam) ? jobIdParam[0] : jobIdParam;
  const [job, setJob] = useState<Job | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [deck, setDeck] = useState<Deck | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCancelling, setIsCancelling] = useState(false);
  const streamRef = useRef<EventSource | null>(null);

  /**
   * Fetch the latest job snapshot from the backend.
   */
  const loadJob = useCallback(async () => {
    if (!jobId) {
      setErrorMessage('Missing job ID.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await api.getJob(jobId);
      setJob(response);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load job';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadJob();
  }, [loadJob]);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    const terminalStatuses: Array<Job['status']> = [
      'completed',
      'failed',
      'cancelled',
    ];

    if (job && terminalStatuses.includes(job.status)) {
      return;
    }

    const interval = window.setInterval(() => {
      loadJob();
    }, 2500);

    return () => {
      window.clearInterval(interval);
    };
  }, [job, jobId, loadJob]);

  useEffect(() => {
    if (!jobId) {
      setEvents([]);
      return;
    }

    let isActive = true;
    const loadEvents = async () => {
      try {
        const data = await api.listJobEvents(String(jobId), 200);
        if (isActive) {
          setEvents(data);
        }
      } catch {
        if (isActive) {
          setEvents([]);
        }
      }
    };

    loadEvents();
    const interval = window.setInterval(loadEvents, 2000);
    return () => {
      isActive = false;
      window.clearInterval(interval);
    };
  }, [jobId]);

  useEffect(() => {
    if (!job) {
      setProject(null);
      setDeck(null);
      return;
    }

    api
      .getProject(job.project_id)
      .then(setProject)
      .catch(() => setProject(null));

    if (job.deck_id) {
      api
        .getDeck(job.deck_id)
        .then(setDeck)
        .catch(() => setDeck(null));
    } else {
      setDeck(null);
    }
  }, [job]);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    if (job?.status !== 'running') {
      streamRef.current?.close();
      streamRef.current = null;
      return;
    }

    const source = new EventSource(`${API_BASE}/api/v1/jobs/${jobId}/stream`);
    streamRef.current = source;

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { progress: number; step: string };
        setJob((current) =>
          current
            ? { ...current, progress: data.progress, current_step: data.step }
            : current
        );
      } catch {
        // ignore parse errors
      }
    };

    source.onerror = () => {
      source.close();
      streamRef.current = null;
    };

    return () => {
      source.close();
      streamRef.current = null;
    };
  }, [jobId, job?.status]);

  /**
   * Cancel the pending or running job and refresh the details.
   */
  const handleCancel = useCallback(async () => {
    if (!jobId || !job) {
      return;
    }

    if (job.status !== 'pending' && job.status !== 'running') {
      return;
    }

    setIsCancelling(true);
    setErrorMessage(null);

    try {
      await api.cancelJob(jobId);
      await loadJob();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to cancel job';
      setErrorMessage(message);
    } finally {
      setIsCancelling(false);
    }
  }, [job, jobId, loadJob]);

  /**
   * Choose the UI icon that matches the current job status.
   */
  const statusIcon = useMemo(() => {
    switch (job?.status) {
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
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  }, [job?.status]);

  /**
   * Render a badge that reflects the job status.
   */
  const statusBadge = useMemo(() => {
    const state = job?.status ?? 'pending';
    const styles = {
      pending: 'bg-gray-100 text-gray-700',
      running: 'bg-primary-100 text-primary-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
      cancelled: 'bg-gray-100 text-gray-700',
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[state]}`}>
        {state.charAt(0).toUpperCase() + state.slice(1)}
      </span>
    );
  }, [job?.status]);

  const canCancel = job && (job.status === 'pending' || job.status === 'running');

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job details</h1>
          <p className="text-sm text-gray-500">
            {jobId ? `Job ${jobId}` : 'No job selected'}
          </p>
        </div>
        <Link
          href="/dashboard"
          className="px-3 py-1 text-sm text-primary-600 hover:text-primary-700"
        >
          ← Back to dashboard
        </Link>
      </div>

      {errorMessage ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {errorMessage}
        </div>
      ) : isLoading ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
          Loading job...
        </div>
      ) : !job ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
          Job not found.
        </div>
      ) : (
        <div className="rounded-lg border bg-white">
          <div className="px-6 py-5 border-b">
            <div className="flex items-center gap-3">
              {statusIcon}
              <h2 className="text-lg font-semibold text-gray-900">
                {job.job_type.replace('_', ' ')}
              </h2>
              {statusBadge}
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Started {new Date(job.created_at).toLocaleString()}
            </p>
            {job.status === 'failed' && job.error_message && (
              <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <p className="font-semibold">Failure reason</p>
                <p className="mt-1 whitespace-pre-wrap">{job.error_message}</p>
              </div>
            )}
          </div>

          <div className="px-6 py-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">
                  Project
                </p>
                {project ? (
                  <Link
                    href={`/projects/${project.id}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-700"
                  >
                    {project.name}
                  </Link>
                ) : (
                  <p className="text-sm text-gray-600">{job.project_id}</p>
                )}
              </div>
              {job.deck_id && (
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-500">
                    Deck
                  </p>
                  {deck ? (
                    <Link
                      href={`/review?deckId=${deck.id}`}
                      className="text-sm font-medium text-primary-600 hover:text-primary-700"
                    >
                      {deck.name}
                    </Link>
                  ) : (
                    <p className="text-sm text-gray-600">{job.deck_id}</p>
                  )}
                </div>
              )}
            </div>

            <div className="mt-6 space-y-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">
                  Progress
                </p>
                <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                  <span>{job.current_step || 'Queued'}</span>
                  <span>{job.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500">
                  Identifiers
                </p>
                <div className="text-sm text-gray-600">
                  <p>Job ID: {job.id}</p>
                  {job.document_id && <p>Document ID: {job.document_id}</p>}
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={isCancelling || !canCancel}
                  onClick={handleCancel}
                  className="px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-red-700 transition-colors"
                >
                  {isCancelling ? 'Cancelling…' : 'Cancel job'}
                </button>
                {job.deck_id && job.status === 'completed' && (
                  <Link
                    href={`/review?deckId=${job.deck_id}`}
                    className="px-4 py-2 text-sm font-semibold text-primary-600 border border-primary-600 rounded-lg hover:bg-primary-50 transition-colors"
                  >
                    Review deck
                  </Link>
                )}
              </div>

              <div className="mt-8">
                <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">
                  Activity log
                </p>
                {events.length === 0 ? (
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
                    No events recorded yet.
                  </div>
                ) : (
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
                    {events.map((event) => (
                      <div key={event.id} className="text-sm text-gray-700">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <span className="font-semibold">{event.level}</span>
                            {event.step ? (
                              <span className="ml-2 text-gray-600">{event.step}</span>
                            ) : null}
                            <p className="mt-1 whitespace-pre-wrap break-words">
                              {event.message}
                            </p>
                          </div>
                          <div className="text-xs text-gray-400 whitespace-nowrap">
                            {new Date(event.created_at).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
