import { useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../lib/auth.js'
import { renderMarkdown } from '../lib/safeHtml.js'
import Evidence from './Evidence.jsx'
import EvidenceGraph from './EvidenceGraph.jsx'
import CaseTimeline from './CaseTimeline.jsx'
import ContradictionsView from './ContradictionsView.jsx'

const API_BASE = import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL || 'http://localhost:8080'

const TABS = [
  { id: 'overview', label: 'Overview', icon: '⌂' },
  { id: 'evidence_graph', label: 'Evidence Graph', icon: '🕸️' },
  { id: 'timeline', label: 'Timeline', icon: '📅' },
  { id: 'contradictions', label: 'Contradictions', icon: '⚠️' },
  { id: 'documents', label: 'Documents', icon: '📄' },
  { id: 'moot', label: 'Moot Court', icon: '⚖️' },
  { id: 'ask', label: 'Ask LEXAI', icon: '✧' },
]

function friendly(e) {
  const m = e?.message || String(e || 'Something went wrong.')
  if (/429|rate limit|too many/i.test(m)) return 'AI provider is temporarily busy. Your case data is safe; please retry shortly.'
  if (/422|validation/i.test(m)) return 'Please complete the required field before continuing.'
  if (/502|provider/i.test(m)) return 'The AI provider could not complete this analysis. Your case data is safe.'
  if (/network|failed to fetch|cannot reach/i.test(m)) return 'Network error. Check your connection and try again.'
  return m
}

export default function CaseWorkspace({
  activeCase,
  capabilities = {},
  onCaseChanged,
  onBack,
  globalCorpusAvailable = false,
  onOpenMootCourt,
}) {
  const [tab, setTab] = useState('overview')
  const [docs, setDocs] = useState([])
  const [intel, setIntel] = useState(null)
  const [intelStatus, setIntelStatus] = useState('checking')
  const [toast, setToast] = useState(null)
  const [busy, setBusy] = useState(false)
  const [analysisStage, setAnalysisStage] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  // Feature Data States
  const [evidenceGraph, setEvidenceGraph] = useState(null)
  const [loadingGraph, setLoadingGraph] = useState(false)
  const [timelineData, setTimelineData] = useState(null)
  const [loadingTimeline, setLoadingTimeline] = useState(false)
  const [contradictionsData, setContradictionsData] = useState(null)
  const [loadingContradictions, setLoadingContradictions] = useState(false)

  // Ask LEXAI in case workspace state
  const [caseQuery, setCaseQuery] = useState('')
  const [queryAnswer, setQueryAnswer] = useState(null)
  const [queryLoading, setQueryLoading] = useState(false)

  // Document Viewer Modal/Drawer
  const [viewer, setViewer] = useState(null)
  const [viewerUrl, setViewerUrl] = useState(null)

  // Moot Court issue state
  const [mootIssue, setMootIssue] = useState('')
  const [mootResult, setMootResult] = useState(null)
  const [mootLoading, setMootLoading] = useState(false)

  const req = async (path, opt = {}) => {
    const res = await apiFetch(`${API_BASE}${path}`, opt)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Request failed (${res.status})`)
    }
    return res.json()
  }

  // Initial load of documents and cached intelligence
  const loadCaseData = async () => {
    if (!activeCase?.id) return
    try {
      const docRes = await req(`/cases/${activeCase.id}/documents`)
      setDocs(docRes.documents || [])
      const intelRes = await req(`/cases/${activeCase.id}/intelligence`)
      setIntel(intelRes.intelligence || null)
      setIntelStatus(intelRes.status || 'ready')
    } catch (e) {
      console.warn('Failed to load initial case data:', e)
    }
  }

  useEffect(() => {
    loadCaseData()
  }, [activeCase?.id])

  // Lazy-load Feature 1 (Evidence Graph)
  useEffect(() => {
    if (tab === 'evidence_graph' && !evidenceGraph && activeCase?.id) {
      setLoadingGraph(true)
      req(`/cases/${activeCase.id}/evidence-graph`)
        .then((data) => setEvidenceGraph(data))
        .catch((err) => setToast({ type: 'error', text: friendly(err) }))
        .finally(() => setLoadingGraph(false))
    }
  }, [tab, activeCase?.id, evidenceGraph])

  // Lazy-load Feature 4 (Timeline)
  useEffect(() => {
    if (tab === 'timeline' && !timelineData && activeCase?.id) {
      setLoadingTimeline(true)
      req(`/cases/${activeCase.id}/timeline`)
        .then((data) => setTimelineData(data))
        .catch((err) => setToast({ type: 'error', text: friendly(err) }))
        .finally(() => setLoadingTimeline(false))
    }
  }, [tab, activeCase?.id, timelineData])

  // Lazy-load Feature 5 (Contradictions)
  useEffect(() => {
    if (tab === 'contradictions' && !contradictionsData && activeCase?.id) {
      setLoadingContradictions(true)
      req(`/cases/${activeCase.id}/contradictions`)
        .then((data) => setContradictionsData(data))
        .catch((err) => setToast({ type: 'error', text: friendly(err) }))
        .finally(() => setLoadingContradictions(false))
    }
  }, [tab, activeCase?.id, contradictionsData])

  // Trigger Case Intelligence analysis
  const runAnalysis = async () => {
    setBusy(true)
    setAnalysisStage('Initiating Case Intelligence…')
    setToast({ type: 'info', text: 'Starting full Case Intelligence extraction…' })
    try {
      const started = await req(`/cases/${activeCase.id}/intelligence/analyze`, { method: 'POST' })
      const jobId = started.job_id
      const deadline = Date.now() + 180000
      let finalJob = null
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 2200))
        const j = await req(`/cases/${activeCase.id}/intelligence/status/${jobId}`)
        setAnalysisStage(j.message || j.stage || 'Analyzing case…')
        if (j.status === 'completed') {
          finalJob = j
          break
        }
        if (j.status === 'failed') throw new Error(j.error?.message || j.message || 'Case Intelligence failed')
      }
      if (!finalJob) throw new Error('Analysis timed out. Please retry shortly.')
      const d = finalJob.result || {}
      setIntel(d.intelligence || null)
      setIntelStatus(d.status || 'ready')
      // Reset lazy caches to pick up new intelligence
      setEvidenceGraph(null)
      setTimelineData(null)
      setContradictionsData(null)
      setToast({ type: 'success', text: 'Case Intelligence ready! Graph, Timeline & Contradictions updated.' })
    } catch (e) {
      setToast({ type: 'error', text: friendly(e) })
    } finally {
      setBusy(false)
      setAnalysisStage('')
    }
  }

  // Open PDF viewer by filename
  const openPdfByName = async (docName) => {
    const d = docs.find((x) => x.name === docName || x.original_name === docName)
    if (d) {
      openPdf(d)
    } else if (docs.length > 0) {
      openPdf(docs[0])
    }
  }

  const openPdf = async (doc) => {
    try {
      setToast({ type: 'info', text: `Loading ${doc.name || doc.original_name}…` })
      const r = await apiFetch(`${API_BASE}/cases/${activeCase.id}/documents/${doc.id}/file`)
      if (!r.ok) throw new Error('Could not open this PDF.')
      const blob = await r.blob()
      if (viewerUrl) URL.revokeObjectURL(viewerUrl)
      const url = URL.createObjectURL(blob)
      setViewer(doc)
      setViewerUrl(url)
      setToast(null)
    } catch (e) {
      setToast({ type: 'error', text: friendly(e) })
    }
  }

  const handleUpload = async (e) => {
    const files = [...e.target.files]
    if (!files.length) return
    setUploading(true)
    try {
      const form = new FormData()
      files.forEach((f) => form.append('files', f))
      await req(`/cases/${activeCase.id}/documents`, { method: 'POST', body: form })
      await loadCaseData()
      await onCaseChanged?.()
      setToast({ type: 'success', text: `Uploaded ${files.length} document${files.length > 1 ? 's' : ''}. Analyzing case…` })
      setTimeout(() => runAnalysis(), 500)
    } catch (err) {
      setToast({ type: 'error', text: friendly(err) })
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleCaseQuery = async (e) => {
    e?.preventDefault?.()
    if (!caseQuery.trim()) return
    setQueryLoading(true)
    try {
      const res = await req(`/cases/${activeCase.id}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: caseQuery.trim(),
          mode: globalCorpusAvailable ? 'both' : 'case',
          top_k: 4,
          verify: true,
        }),
      })
      setQueryAnswer(res)
    } catch (err) {
      setToast({ type: 'error', text: friendly(err) })
    } finally {
      setQueryLoading(false)
    }
  }

  const handleCaseMoot = async (e) => {
    e?.preventDefault?.()
    if (!mootIssue.trim()) return
    setMootLoading(true)
    try {
      const res = await req(`/cases/${activeCase.id}/moot-court`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issue: mootIssue.trim() }),
      })
      setMootResult(res)
    } catch (err) {
      setToast({ type: 'error', text: friendly(err) })
    } finally {
      setMootLoading(false)
    }
  }

  return (
    <section className="unified-case-workspace page-enter">
      {/* Toast banner */}
      {toast && (
        <div className={`lex-toast ${toast.type}`}>
          <span>{toast.type === 'error' ? '!' : '✓'}</span>
          <div>{toast.text}</div>
          <button onClick={() => setToast(null)}>✕</button>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,application/pdf"
        style={{ display: 'none' }}
        onChange={handleUpload}
      />

      {/* ── TOP UNIFIED WORKSPACE HEADER ── */}
      <header className="workspace-header">
        <div className="header-breadcrumbs">
          <button className="back-to-cases" onClick={onBack}>← Back to My Cases</button>
          <span className="case-status-badge active">● Private Case Workspace</span>
        </div>

        <div className="case-title-row">
          <div className="case-identity">
            <h1 className="case-main-title">{activeCase.title}</h1>
            <p className="case-subtitle">{activeCase.description || 'Isolated research workspace with verified evidence graph and provenance tracking.'}</p>
          </div>

          <div className="case-quick-actions">
            <button
              className="btn-action-primary"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? 'Uploading…' : '＋ Add Case PDFs'}
            </button>
            <button
              className="btn-action-secondary"
              disabled={busy || docs.length === 0}
              onClick={runAnalysis}
              title="Run or refresh Case Intelligence"
            >
              {busy ? (analysisStage || 'Analyzing…') : '⚡ Run Intelligence'}
            </button>
          </div>
        </div>

        {/* Unified Tab Bar */}
        <nav className="workspace-tabs-bar" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              className={`workspace-tab ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              <span className="tab-icon">{t.icon}</span>
              <span className="tab-label">{t.label}</span>
              {t.id === 'contradictions' && intel?.contradictions?.length > 0 && (
                <span className="tab-badge-alert">{intel.contradictions.length}</span>
              )}
            </button>
          ))}
        </nav>
      </header>

      {/* ── TWO-COLUMN MAIN WORKSPACE LAYOUT ── */}
      <div className="workspace-grid-layout">
        {/* LEFT / MAIN VIEW CONTAINER */}
        <main className="workspace-main-column">
          {/* Tab 1: OVERVIEW */}
          {tab === 'overview' && (
            <div className="tab-view overview-view">
              <div className="overview-hero-card">
                <div className="hero-text">
                  <span className="hero-tag">CASE INTELLIGENCE OVERVIEW</span>
                  <h2>{intel ? 'Case Mapped with Full Provenance' : 'Ready for Automated Analysis'}</h2>
                  <p>
                    {intel?.summary
                      ? intel.summary
                      : 'Upload case PDFs to automatically construct the Evidence Graph, Chronological Timeline, and Cross-Document Contradiction Detector.'}
                  </p>
                </div>
                <div className="hero-stats-row">
                  <div className="hero-stat">
                    <strong>{docs.length}</strong>
                    <span>Documents</span>
                  </div>
                  <div className="hero-stat">
                    <strong>{intel?.parties?.length || 0}</strong>
                    <span>Parties</span>
                  </div>
                  <div className="hero-stat">
                    <strong>{intel?.legal_issues?.length || 0}</strong>
                    <span>Legal Issues</span>
                  </div>
                  <div className="hero-stat">
                    <strong>{intel?.evidence?.length || 0}</strong>
                    <span>Evidence Items</span>
                  </div>
                </div>
              </div>

              {/* Quick Navigation Cards */}
              <div className="quick-access-grid">
                <div className="access-card" onClick={() => setTab('evidence_graph')}>
                  <span className="card-emoji">🕸️</span>
                  <h4>Evidence & Claim Graph</h4>
                  <p>Interactive relational network of claims, statutes, witnesses, and exhibits.</p>
                  <span className="card-link">Explore Graph →</span>
                </div>
                <div className="access-card" onClick={() => setTab('timeline')}>
                  <span className="card-emoji">📅</span>
                  <h4>Case Timeline</h4>
                  <p>Chronological milestones and date conflict detection across records.</p>
                  <span className="card-link">View Timeline →</span>
                </div>
                <div className="access-card" onClick={() => setTab('contradictions')}>
                  <span className="card-emoji">⚠️</span>
                  <h4>Contradiction Detector</h4>
                  <p>Cross-document discrepancies in witness statements, amounts, and dates.</p>
                  <span className="card-link">Review Clashes →</span>
                </div>
                <div className="access-card" onClick={() => setTab('moot')}>
                  <span className="card-emoji">⚖️</span>
                  <h4>Case Moot Court</h4>
                  <p>Adversarial AI debate strictly grounded on your case documents.</p>
                  <span className="card-link">Enter Courtroom →</span>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: EVIDENCE GRAPH */}
          {tab === 'evidence_graph' && (
            <div className="tab-view graph-view">
              <div className="view-header">
                <div>
                  <span className="view-eyebrow">FEATURE 1 · CASE INTELLIGENCE</span>
                  <h3>Legal Evidence & Claim Graph</h3>
                </div>
                <button
                  className="btn-refresh"
                  onClick={() => {
                    setEvidenceGraph(null)
                    setTab('evidence_graph')
                  }}
                >
                  ↻ Re-extract Graph
                </button>
              </div>
              <EvidenceGraph
                graphData={evidenceGraph}
                loading={loadingGraph}
                onOpenDocument={openPdfByName}
              />
            </div>
          )}

          {/* Tab 3: TIMELINE */}
          {tab === 'timeline' && (
            <div className="tab-view timeline-view">
              <div className="view-header">
                <div>
                  <span className="view-eyebrow">FEATURE 4 · CASE CHRONOLOGY</span>
                  <h3>Automatic Case Timeline & Date Conflicts</h3>
                </div>
                <button
                  className="btn-refresh"
                  onClick={() => {
                    setTimelineData(null)
                    setTab('timeline')
                  }}
                >
                  ↻ Refresh Timeline
                </button>
              </div>
              <CaseTimeline
                timelineData={timelineData}
                loading={loadingTimeline}
                onOpenDocument={openPdfByName}
              />
            </div>
          )}

          {/* Tab 4: CONTRADICTIONS */}
          {tab === 'contradictions' && (
            <div className="tab-view contradictions-view">
              <div className="view-header">
                <div>
                  <span className="view-eyebrow">FEATURE 5 · EVIDENTIARY AUDIT</span>
                  <h3>Cross-Document Contradiction Detector</h3>
                </div>
                <button
                  className="btn-refresh"
                  onClick={() => {
                    setContradictionsData(null)
                    setTab('contradictions')
                  }}
                >
                  ↻ Scan Discrepancies
                </button>
              </div>
              <ContradictionsView
                contradictionsData={contradictionsData}
                loading={loadingContradictions}
                onOpenDocument={openPdfByName}
              />
            </div>
          )}

          {/* Tab 5: DOCUMENTS */}
          {tab === 'documents' && (
            <div className="tab-view documents-view">
              <div className="view-header">
                <div>
                  <span className="view-eyebrow">CASE DOSSIER</span>
                  <h3>Uploaded Evidence Documents ({docs.length})</h3>
                </div>
                <button className="btn-action-primary" onClick={() => fileInputRef.current?.click()}>
                  ＋ Upload More PDFs
                </button>
              </div>

              {docs.length === 0 ? (
                <div className="empty-graph-state">
                  <span className="empty-icon">📂</span>
                  <h3>No documents uploaded yet</h3>
                  <p>Add case pleadings, charge-sheets, FIRs, or legal notices to enable Case Intelligence.</p>
                </div>
              ) : (
                <div className="doc-list-grid">
                  {docs.map((d) => (
                    <div key={d.id} className="doc-card">
                      <div className="doc-card-icon">📄</div>
                      <div className="doc-card-info">
                        <strong>{d.name || d.original_name}</strong>
                        <small>{(d.size_bytes / 1024).toFixed(0)} KB · Uploaded</small>
                      </div>
                      <button className="btn-open-pdf" onClick={() => openPdf(d)}>
                        Inspect PDF →
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 6: MOOT COURT */}
          {tab === 'moot' && (
            <div className="tab-view moot-view">
              <div className="view-header">
                <div>
                  <span className="view-eyebrow">FEATURE 3 · ADVERSARIAL ARENA</span>
                  <h3>Case-Aware Moot Court Simulation</h3>
                </div>
              </div>

              <form onSubmit={handleCaseMoot} className="case-moot-form">
                <label className="input-label">Legal Proposition or Disputed Question</label>
                <textarea
                  className="case-textarea"
                  rows={3}
                  value={mootIssue}
                  onChange={(e) => setMootIssue(e.target.value)}
                  placeholder="e.g. Whether liability attaches under Section 138 when statutory notice was returned unserved..."
                />
                <button
                  type="submit"
                  className="btn-action-primary"
                  disabled={mootIssue.trim().length < 5 || mootLoading}
                >
                  {mootLoading ? 'Simulating Courtroom Debate…' : '⚖️ Commence Case-Grounded Moot'}
                </button>
              </form>

              {mootResult && (
                <div className="moot-case-result">
                  <div className="disposition-strip">
                    <span>DISPOSITION:</span>
                    <strong>{mootResult.bench?.disposition || mootResult.disposition}</strong>
                    <span className="winner-pill">Prevailing: {mootResult.bench?.prevailing_party || mootResult.winner}</span>
                  </div>

                  <div className="counsel-pods">
                    <div className="counsel-pod pet">
                      <h4>Senior Counsel for Petitioner</h4>
                      <p>{mootResult.petitioner?.argument}</p>
                    </div>
                    <div className="counsel-pod resp">
                      <h4>Senior Counsel for Respondent</h4>
                      <p>{mootResult.respondent?.argument}</p>
                    </div>
                  </div>

                  <div className="bench-verdict-box">
                    <h4>🏛️ Presiding Judicial Order</h4>
                    <p>{mootResult.bench?.verdict}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 7: ASK LEXAI */}
          {tab === 'ask' && (
            <div className="tab-view ask-view">
              <div className="view-header">
                <div>
                  <span className="view-eyebrow">CASE RAG ENGINE</span>
                  <h3>Ask LEXAI over Case Records</h3>
                </div>
              </div>

              <form onSubmit={handleCaseQuery} className="case-query-form">
                <input
                  type="text"
                  className="case-input"
                  value={caseQuery}
                  onChange={(e) => setCaseQuery(e.target.value)}
                  placeholder="Ask any question strictly grounded on this case's documents..."
                />
                <button type="submit" className="btn-action-primary" disabled={queryLoading}>
                  {queryLoading ? 'Retrieving…' : 'Ask LEXAI'}
                </button>
              </form>

              {queryAnswer && (
                <div className="case-query-answer">
                  <div className="answer-text">
                    {renderMarkdown(queryAnswer.answer)}
                  </div>
                  {queryAnswer.sources?.length > 0 && (
                    <div className="case-sources-list">
                      <span className="sources-title">RETRIEVED CASE EXCERPTS:</span>
                      {queryAnswer.sources.map((s, idx) => (
                        <div key={idx} className="source-item">
                          <strong>{s.source_file || s.case_name} (p.{s.page || 1})</strong>
                          <p>{s.text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </main>

        {/* ── RIGHT INTELLIGENCE PANEL ── */}
        <aside className="workspace-intel-panel" aria-label="Case Intelligence Summary">
          <div className="panel-section-title">
            <span>INTELLIGENCE RADAR</span>
            <span className={`status-dot ${intelStatus === 'ready' ? 'green' : 'amber'}`}>
              {intelStatus === 'ready' ? 'Ready' : 'Outdated'}
            </span>
          </div>

          {/* 1. Case Summary */}
          <div className="intel-panel-card">
            <span className="card-subhead">CASE SUMMARY</span>
            <p className="summary-text">
              {intel?.summary || 'Upload case files and click "Run Intelligence" to populate.'}
            </p>
          </div>

          {/* 2. Litigating Parties */}
          <div className="intel-panel-card">
            <span className="card-subhead">PARTIES ({intel?.parties?.length || 0})</span>
            {intel?.parties?.length > 0 ? (
              <div className="tag-cloud">
                {intel.parties.map((p, i) => (
                  <span key={i} className="party-pill">
                    <strong>{p.name || p.role}:</strong> {p.role || 'Litigant'}
                  </span>
                ))}
              </div>
            ) : (
              <small className="muted-text">No parties identified yet.</small>
            )}
          </div>

          {/* 3. Core Legal Issues */}
          <div className="intel-panel-card">
            <span className="card-subhead">LEGAL ISSUES ({intel?.legal_issues?.length || 0})</span>
            {intel?.legal_issues?.length > 0 ? (
              <ul className="mini-bullet-list">
                {intel.legal_issues.slice(0, 4).map((issue, i) => (
                  <li key={i}>{typeof issue === 'object' ? issue.issue : issue}</li>
                ))}
              </ul>
            ) : (
              <small className="muted-text">Issues not yet mapped.</small>
            )}
          </div>

          {/* 4. Contradictions Alert */}
          {intel?.contradictions?.length > 0 && (
            <div className="intel-panel-card alert-card">
              <span className="card-subhead alert-text">⚠️ CONTRADICTIONS ({intel.contradictions.length})</span>
              <p className="alert-desc">Discrepancies found across witness accounts and filings.</p>
              <button className="panel-btn" onClick={() => setTab('contradictions')}>
                View Contradictions →
              </button>
            </div>
          )}

          {/* 5. Source Documents */}
          <div className="intel-panel-card">
            <span className="card-subhead">SOURCE EXHIBITS ({docs.length})</span>
            <div className="mini-doc-list">
              {docs.slice(0, 5).map((d) => (
                <div key={d.id} className="mini-doc-row" onClick={() => openPdf(d)}>
                  <span>📄 {d.name || d.original_name}</span>
                  <small>View</small>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>

      {/* PDF Source Viewer Drawer */}
      {viewer && viewerUrl && (
        <div className="pdf-drawer">
          <div className="pdf-drawer-head">
            <div>
              <span className="eyebrow">SOURCE EXHIBIT INSPECTOR</span>
              <h3>{viewer.name || viewer.original_name}</h3>
            </div>
            <button
              className="icon-btn"
              onClick={() => {
                URL.revokeObjectURL(viewerUrl)
                setViewer(null)
                setViewerUrl(null)
              }}
            >
              ✕
            </button>
          </div>
          <iframe title={viewer.name || 'PDF Document'} src={viewerUrl} />
        </div>
      )}
    </section>
  )
}
