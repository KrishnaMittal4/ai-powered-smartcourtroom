import { useMemo, useState } from 'react'
import { timeAgo, tabKeys } from '../lib/utils.js'

export default function Sidebar({
  history = [],
  activeId,
  onOpen,
  onNew,
  onToggleSave,
  onDelete,
  onClear,
  open,
  onClose,
  appMode,
  setAppMode,
  onGlobal,
  onCases,
  onMoot,
  onDraft,
  onBnsLens,
  onScanNotice,
  globalCorpusAvailable = false,
  onUploadResearch,
}) {
  const [tab, setTab] = useState('recent')
  const [filter, setFilter] = useState('')

  const items = useMemo(() => {
    const f = filter.trim().toLowerCase()
    return history
      .filter((h) => (tab === 'saved' ? h.saved : true))
      .filter((h) => !f || h.question.toLowerCase().includes(f))
  }, [history, tab, filter])

  return (
    <aside id="sidebar" className={`sidebar ${open ? 'open' : ''}`} aria-label="Smart Courtroom Navigation">
      <div className="sidebar-brand-header">
        <span className="sidebar-brand-mark">⚖️</span>
        <div className="sidebar-brand-title">
          <strong>SMART COURTROOM</strong>
          <small>LEGAL OPERATING SYSTEM</small>
        </div>
      </div>

      <nav className="advocate-nav" aria-label="Platform Tools">
        {/* RESEARCH */}
        <div className="nav-section-header">
          <span className="section-title">RESEARCH</span>
        </div>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onUploadResearch?.()
            onClose()
          }}
        >
          <span className="nav-icon">📄</span>
          <span>Legal Research</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onGlobal?.()
            onClose()
          }}
        >
          <span className="nav-icon">🔍</span>
          <span>Similar Cases</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onBnsLens?.()
            onClose()
          }}
        >
          <span className="nav-icon">⚖️</span>
          <span>BNS ↔ IPC Lens</span>
        </button>

        {/* CASE INTELLIGENCE */}
        <div className="nav-section-header">
          <span className="section-title">CASE INTELLIGENCE</span>
        </div>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onCases?.('overview')
            onClose()
          }}
        >
          <span className="nav-icon">📁</span>
          <span>My Cases</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onCases?.('evidence_graph')
            onClose()
          }}
        >
          <span className="nav-icon">🕸️</span>
          <span>Evidence Graph</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onCases?.('timeline')
            onClose()
          }}
        >
          <span className="nav-icon">⏱️</span>
          <span>Case Timeline</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onCases?.('contradictions')
            onClose()
          }}
        >
          <span className="nav-icon">⚡</span>
          <span>Contradictions</span>
        </button>

        {/* COURTROOM */}
        <div className="nav-section-header">
          <span className="section-title">COURTROOM</span>
        </div>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onMoot?.('ai_vs_ai')
            onClose()
          }}
        >
          <span className="nav-icon">🏛️</span>
          <span>Moot Court</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onMoot?.('human_vs_ai_petitioner')
            onClose()
          }}
        >
          <span className="nav-icon">⚔️</span>
          <span>Human vs AI Practice</span>
        </button>

        {/* TOOLS */}
        <div className="nav-section-header">
          <span className="section-title">TOOLS</span>
        </div>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            setAppMode?.('citizen')
            onClose()
          }}
        >
          <span className="nav-icon">🛡️</span>
          <span>Citizen Legal Advisor</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onScanNotice?.()
            onClose()
          }}
        >
          <span className="nav-icon">📑</span>
          <span>Scan Notice / Contract</span>
        </button>
        <button
          type="button"
          className="nav-item-btn"
          onClick={() => {
            onDraft?.()
            onClose()
          }}
        >
          <span className="nav-icon">✎</span>
          <span>Legal Drafting</span>
        </button>
      </nav>

      {/* SYSTEM & HISTORY */}
      <div className="sidebar-history-section">
        <div className="nav-section-header">
          <span className="section-title">RESEARCH HISTORY</span>
        </div>

        <div
          className="tabs"
          role="tablist"
          aria-label="History"
          onKeyDown={(e) => tabKeys(e, ['recent', 'saved'], tab, setTab, 'hs')}
        >
          <button
            role="tab"
            id="hs-tab-recent"
            aria-controls="hs-panel"
            aria-selected={tab === 'recent'}
            tabIndex={tab === 'recent' ? 0 : -1}
            onClick={() => setTab('recent')}
          >
            Recent
          </button>
          <button
            role="tab"
            id="hs-tab-saved"
            aria-controls="hs-panel"
            aria-selected={tab === 'saved'}
            tabIndex={tab === 'saved' ? 0 : -1}
            onClick={() => setTab('saved')}
          >
            Saved{history.some((h) => h.saved) ? ` (${history.filter((h) => h.saved).length})` : ''}
          </button>
        </div>

        <input
          className="side-search"
          type="search"
          placeholder="Filter prior queries..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filter prior queries"
        />

        <ul
          className="history-list"
          id="hs-panel"
          role="tabpanel"
          aria-labelledby={`hs-tab-${tab}`}
          onKeyDown={(e) => {
            if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
            const btns = [...e.currentTarget.querySelectorAll('.history-item')]
            const i = btns.indexOf(document.activeElement)
            if (i === -1) return
            e.preventDefault()
            btns[Math.min(btns.length - 1, Math.max(0, i + (e.key === 'ArrowDown' ? 1 : -1)))]?.focus()
          }}
        >
          {items.length === 0 && (
            <li className="empty-note">
              {tab === 'saved'
                ? 'Star an answer to keep it saved.'
                : history.length
                ? 'No matching questions found.'
                : 'Your research questions will appear here.'}
            </li>
          )}
          {items.map((h) => (
            <li key={h.id} className={h.id === activeId ? 'active' : ''}>
              <button
                className="history-item"
                aria-current={h.id === activeId ? 'true' : undefined}
                onClick={() => {
                  onOpen(h.id)
                  onClose()
                }}
              >
                <span className="history-q">{h.question}</span>
                <span className="history-meta">{timeAgo(h.ts)}</span>
              </button>
              <button
                className={`icon-btn star ${h.saved ? 'on' : ''}`}
                onClick={() => onToggleSave(h.id)}
                aria-label={h.saved ? 'Remove from saved' : 'Save this answer'}
                title={h.saved ? 'Remove from saved' : 'Save'}
              >
                {h.saved ? '★' : '☆'}
              </button>
              <button
                className="icon-btn"
                onClick={() => onDelete(h.id)}
                aria-label="Delete from history"
                title="Delete"
              >
                ×
              </button>
            </li>
          ))}
        </ul>

        {history.length > 0 && (
          <button
            className="btn-quiet clear-btn"
            onClick={() => {
              if (window.confirm('Delete all saved history from this browser?')) onClear()
            }}
          >
            Clear history
          </button>
        )}
      </div>
    </aside>
  )
}
