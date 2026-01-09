'use client';

import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Zap, CheckCircle } from 'lucide-react';

export default function Home() {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    // TODO: Handle file upload
    console.log('Files:', acceptedFiles);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
  });

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Turn Lecture Slides into Flashcards
        </h1>
        <p className="text-lg text-gray-600 mb-8">
          Upload a PDF and let our AI pipeline extract knowledge, generate
          cards, and help you learn more effectively.
        </p>

        {/* Upload Zone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-12 cursor-pointer transition-colors ${
            isDragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          {isDragActive ? (
            <p className="text-primary-600 font-medium">Drop your PDF here...</p>
          ) : (
            <>
              <p className="text-gray-600 font-medium mb-2">
                Drag and drop a PDF here, or click to select
              </p>
              <p className="text-sm text-gray-400">Supports PDF files only</p>
            </>
          )}
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-16">
          <div className="text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <FileText className="w-6 h-6 text-primary-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Vision-Based</h3>
            <p className="text-sm text-gray-600">
              Works with image-based PDFs, scanned documents, and slides with
              diagrams.
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Zap className="w-6 h-6 text-primary-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">AI Pipeline</h3>
            <p className="text-sm text-gray-600">
              Extract claims, write cards, critique for quality, and deduplicate
              automatically.
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-6 h-6 text-primary-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Human Review</h3>
            <p className="text-sm text-gray-600">
              Review each card with its source slide. Approve, edit, or reject
              before export.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
