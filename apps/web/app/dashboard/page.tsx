'use client';

import { useState, useEffect } from 'react';
import { Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface Job {
  id: string;
  deck_id: string;
  deck_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  created_at: string;
}

// Mock data for demo
const mockJobs: Job[] = [
  {
    id: '1',
    deck_id: 'd1',
    deck_name: 'Biology 101 - Cell Structure',
    status: 'running',
    progress: 45,
    current_step: 'Extracting claims from slide 5/12',
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    deck_id: 'd2',
    deck_name: 'History - World War II',
    status: 'completed',
    progress: 100,
    current_step: 'Done',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
];

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>(mockJobs);

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
    }
  };

  const getStatusBadge = (status: Job['status']) => {
    const styles = {
      pending: 'bg-gray-100 text-gray-700',
      running: 'bg-primary-100 text-primary-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
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

        {jobs.length === 0 ? (
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
                    href={`/decks/${job.deck_id}`}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    View Deck
                  </a>
                </div>

                {job.status === 'running' && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                      <span>{job.current_step}</span>
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
