import React from 'react'

export const LibraryPage: React.FC = () => {
  return (
    <div className="library-page">
      <div className="page-header">
        <div className="page-header-text">
          <h1>My Library</h1>
          <p>Upload your notes to generate quizzes from them. Coming in Phase 3.</p>
        </div>

        <div className="tooltip-wrapper">
          <button type="button" className="btn-primary" disabled>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ marginRight: '6px' }}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload Notes
          </button>
          <span className="tooltip-text">
            Document upload and RAG notes processing will be available in Phase 3.
          </span>
        </div>
      </div>

      <div className="library-empty-state">
        <svg
          className="empty-state-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
        <h3>No documents yet</h3>
        <p>
          Once Phase 3 is implemented, you will be able to upload PDF, DOCX, TXT, and Markdown files to
          ground your quizzes in your personal study materials.
        </p>
      </div>
    </div>
  )
}

export default LibraryPage
