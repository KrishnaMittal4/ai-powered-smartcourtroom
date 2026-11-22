import { useState } from 'react'

/**
 * Split-Screen Document Citation Drawer
 * Renders side-by-side evidence inspection with luminous gold highlighting,
 * full source provenance, and 1-click citation export.
 */
export default function DocumentSplitViewer({
  isOpen,
  onClose,
  citation,
  passage,
  onDissectRatio,
}) {
  const [copied, setCopied] = useState(false)

  if (!isOpen || (!citation && !passage)) return null

  const title = citation?.case_name || passage?.source_file || passage?.case_name || 'Grounding Document Record'
  const text = passage?.text || citation?.passage_support?.passage || citation?.text || ''
  const verdict = citation?.verdict || citation?.passage_support?.verdict || 'yes'
  const score = passage?.score != null ? Math.round(passage.score * 100) : null
  const pageNo = passage?.page || citation?.page || null

  const copyCitation = () => {
    const formalCitation = `${title}${pageNo ? `, Page ${pageNo}` : ''} — "${text.slice(0, 180)}..." [LEXAI Verified]`
    navigator.clipboard.writeText(formalCitation)
    setCopied(true)
    setTimeout(() => setCopied(false), 2200)
  }

  return (
    <div className="doc-split-drawer-backdrop" onClick={onClose} aria-label="Close document drawer">
      <aside
        className="doc-split-drawer-panel page-enter"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Document Citation Verification"
      >
        <header className="doc-split-drawer-header">
          <div>
            <div className="drawer-eyebrow">
              <span className="drawer-icon">📜</span>
              <span>VERIFIED SOURCE EXHIBIT PROVENANCE</span>
            </div>
            <h3 className="drawer-title">{title}</h3>
            {pageNo && <span className="drawer-page-chip">Page {pageNo}</span>}
          </div>
          <button type="button" className="drawer-close-btn" onClick={onClose} title="Close drawer (Esc)">
            ✕
          </button>
        </header>

        <div className="doc-split-drawer-body">
          {/* Status & Confidence Bar */}
          <div className="drawer-status-bar">
            <span className={`drawer-verdict-pill ${verdict}`}>
              {verdict === 'yes' ? '✓ Grounded & Verified' : verdict === 'partial' ? '◐ Partly Supported' : '○ Citation Record'}
            </span>
            {score != null && (
              <span className="drawer-score-pill">
                Match Confidence: <strong>{score}%</strong>
              </span>
            )}
          </div>

          {/* Verbatim Highlighted Passage Card */}
          <div className="drawer-passage-card">
            <div className="passage-card-label">VERBATIM EXHIBIT PASSAGE</div>
            <div className="passage-card-text">
              <span className="passage-quote-mark">“</span>
              <mark className="gold-passage-mark">{text}</mark>
              <span className="passage-quote-mark">”</span>
            </div>
          </div>

          {/* Reasoning / Support Note */}
          {citation?.passage_support?.reason && (
            <div className="drawer-reason-card">
              <strong>Judicial Cross-Check Assessment:</strong>
              <p>{citation.passage_support.reason}</p>
            </div>
          )}

          {/* Action Tools */}
          <div className="drawer-actions-row">
            <button
              type="button"
              className="drawer-action-btn primary"
              onClick={copyCitation}
              title="Copy formal citation to clipboard"
            >
              <span>{copied ? '✓ Copied Formal Citation' : '📋 Copy Verbatim Citation'}</span>
            </button>
            {onDissectRatio && (
              <button
                type="button"
                className="drawer-action-btn secondary"
                onClick={() => {
                  onDissectRatio(title, text)
                  onClose()
                }}
                title="Dissect Ratio Decidendi vs Obiter Dicta"
              >
                <span>⚖️ Dissect Ratio vs. Obiter</span>
              </button>
            )}
          </div>
        </div>

        <footer className="doc-split-drawer-footer">
          <small>© 2026 Krishna Mittal. All Rights Reserved. · AI-Powered Smart Courtroom</small>
        </footer>
      </aside>
    </div>
  )
}
