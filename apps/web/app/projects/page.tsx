/**
 * Project list page.
 */
'use client';

import { useCallback, useEffect, useState } from 'react';
import { Folder, Plus } from 'lucide-react';

import { api, Project } from '@/lib/api';

/**
 * Render the projects list view.
 */
export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /**
   * Load projects from the API.
   */
  const loadProjects = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.listProjects();
      setProjects(data);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load projects';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-500 text-sm">
            Organize documents into projects and generate decks per chapter.
          </p>
        </div>
        <a
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Project
        </a>
      </div>

      {errorMessage ? (
        <div className="bg-white rounded-lg border p-12 text-center text-red-600">
          {errorMessage}
        </div>
      ) : isLoading ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-500">
          Loading projects...
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-white rounded-lg border p-12 text-center">
          <Folder className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No projects yet
          </h3>
          <p className="text-gray-500 mb-4">
            Upload documents to create your first project.
          </p>
          <a
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4" />
            Start a project
          </a>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <a
              key={project.id}
              href={`/projects/${project.id}`}
              className="bg-white rounded-lg border hover:shadow-md transition-shadow p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <Folder className="w-5 h-5 text-primary-500" />
                <h2 className="font-semibold text-gray-900 line-clamp-1">
                  {project.name}
                </h2>
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <div>{project.document_count} documents</div>
                <div>{project.deck_count} decks</div>
              </div>
              <div className="text-xs text-gray-400 mt-3">
                Updated {new Date(project.updated_at).toLocaleString()}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
