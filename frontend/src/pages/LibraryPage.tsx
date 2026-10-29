import React, { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { listDocuments, uploadDocument, deleteDocument, DocumentItem } from '../api/documents'

export const LibraryPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const fetchDocs = async () => {
    try {
      const data = await listDocuments()
      setDocuments(data)
    } catch (e: any) {
      console.warn('Could not fetch documents:', e)
    }
  }

  useEffect(() => {
    fetchDocs()
    // Poll processing status every 4 seconds if any doc is in 'processing'
    const interval = setInterval(() => {
      if (documents.some((d) => d.status === 'processing')) {
        fetchDocs()
      }
    }, 4000)
    return () => clearInterval(interval)
  }, [documents])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)
    try {
      await uploadDocument(file)
      await fetchDocs()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to upload document.')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this document and all its indexed chunks?')) return
    try {
      await deleteDocument(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
    } catch (err: any) {
      alert('Failed to delete document.')
    }
  }

  return (
    <div style={{ maxWidth: '900px', margin: '2rem auto', padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.75rem' }}>My Notes Library</h1>
          <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-secondary)' }}>
            Upload PDFs, DOCX, or text notes to generate personalized quizzes with verified citations.
          </p>
        </div>

        <div>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept=".pdf,.docx,.txt,.md"
            onChange={handleFileChange}
          />
          <button
            className="btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading...' : '⬆ Upload Notes'}
          </button>
        </div>
      </div>

      {error && (
        <div className="form-alert-error" style={{ marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Action Banner to Create Notes Quiz */}
      {documents.some((d) => d.status === 'ready') && (
        <div
          className="card"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1.25rem 1.5rem',
            marginBottom: '2rem',
            border: '1px solid var(--accent)',
            backgroundColor: 'rgba(99, 102, 241, 0.08)',
          }}
        >
          <div>
            <strong style={{ fontSize: '1.1rem', display: 'block' }}>Ready to practice?</strong>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              You have processed study materials ready for quiz generation.
            </span>
          </div>
          <Link to="/quiz/create" className="btn-primary" style={{ textDecoration: 'none' }}>
            Generate Quiz from Notes
          </Link>
        </div>
      )}

      {/* Document List Table */}
      {documents.length === 0 ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📄</div>
          <h3>Your library is empty</h3>
          <p>Upload your lecture slides, notes, or reading assignments to get started.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-primary)' }}>
                <th style={{ padding: '1rem' }}>Filename</th>
                <th style={{ padding: '1rem' }}>Type</th>
                <th style={{ padding: '1rem' }}>Size</th>
                <th style={{ padding: '1rem' }}>Status</th>
                <th style={{ padding: '1rem' }}>Chunks</th>
                <th style={{ padding: '1rem', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '1rem', fontWeight: 600 }}>{doc.filename}</td>
                  <td style={{ padding: '1rem', textTransform: 'uppercase', fontSize: '0.85rem' }}>{doc.file_type}</td>
                  <td style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    {(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <span
                      style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        backgroundColor:
                          doc.status === 'ready'
                            ? 'rgba(16, 185, 129, 0.15)'
                            : doc.status === 'processing'
                            ? 'rgba(251, 191, 36, 0.15)'
                            : 'rgba(239, 68, 68, 0.15)',
                        color:
                          doc.status === 'ready'
                            ? 'var(--success)'
                            : doc.status === 'processing'
                            ? '#fbbf24'
                            : 'var(--error)',
                      }}
                    >
                      {doc.status}
                    </span>
                  </td>
                  <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>
                    {doc.total_chunks > 0 ? doc.total_chunks : '-'}
                  </td>
                  <td style={{ padding: '1rem', textAlign: 'right' }}>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--error)',
                        cursor: 'pointer',
                        fontWeight: 600,
                      }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
export default LibraryPage
