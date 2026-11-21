import { useState, useMemo } from 'react'

const CATEGORY_NAMES = {
  dates: 'Dates & Chronology',
  times: 'Timing of Incident',
  locations: 'Locations & Scene of Crime',
  amounts: 'Monetary Amounts & Value',
  identities: 'Identities & Capacities',
  witness_statements: 'Witness Depositions',
  document_assertions: 'Document Assertions & Notice',
  factual_claims: 'Factual Claims',
}

export default function ContradictionsView({ contradictionsData, onOpenDocument, loading = false }) {
  const [activeCategory, setActiveCategory] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL') // 'ALL', 'confirmed', 'possible'

  const items = useMemo(() => contradictionsData?.contradictions || [], [contradictionsData])
  const summary = useMemo(() => contradictionsData?.summary || { total: 0, confirmed: 0, possible: 0 }, [contradictionsData])

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const matchCat = activeCategory === 'ALL' || item.category === activeCategory
      const matchStatus = statusFilter === 'ALL' || item.status === statusFilter
      return matchCat && matchStatus
    })
  }, [items, activeCategory, statusFilter])

  const categories = useMemo(() => {
    return Array.from(new Set(items.map((i) => i.category)))
  }, [items])

  if (loading) {
    return (
      <div className="contradictions-loading">
        <div className="graph-spinner" />
        <p>Scanning Cross-Document Inconsistencies…</p>
        <small>Running semantic & NLI verification across uploaded exhibits</small>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="empty-graph-state">
        <span className="empty-icon">🤝</span>
        <h3>No Direct Contradictions Detected</h3>
        <p>
          {summary.note || 'The uploaded documents present mutually consistent factual assertions without irreconcilable clashes.'}
        </p>
      </div>
    )
  }

  return (
    <div className="contradictions-container">
      {/* Summary KPI Strip */}
      <div className="contradiction-summary-strip">
        <div className="summary-stat">
          <span className="stat-num">{summary.total || items.length}</span>
          <span className="stat-label">Total Inconsistencies</span>
        </div>
        <div className="summary-stat confirmed">
          <span className="stat-num">{summary.confirmed || 0}</span>
          <span className="stat-label">Confirmed Clashes</span>
        </div>
        <div className="summary-stat possible">
          <span className="stat-num">{summary.possible || 0}</span>
          <span className="stat-label">Possible Discrepancies</span>
        </div>
      </div>

      {/* Filter Row */}
      <div className="contradiction-toolbar">
        <div className="status-toggle-row">
          <button
            className={`toggle-btn ${statusFilter === 'ALL' ? 'active' : ''}`}
            onClick={() => setStatusFilter('ALL')}
          >
            All Severity
          </button>
          <button
            className={`toggle-btn confirmed ${statusFilter === 'confirmed' ? 'active' : ''}`}
            onClick={() => setStatusFilter('confirmed')}
          >
            🚨 Confirmed Only
          </button>
          <button
            className={`toggle-btn possible ${statusFilter === 'possible' ? 'active' : ''}`}
            onClick={() => setStatusFilter('possible')}
          >
            ⚠️ Possible Only
          </button>
        </div>

        {categories.length > 1 && (
          <div className="category-select-wrapper">
            <label htmlFor="cat-filter">Category:</label>
            <select
              id="cat-filter"
              value={activeCategory}
              onChange={(e) => setActiveCategory(e.target.value)}
            >
              <option value="ALL">All Categories ({items.length})</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_NAMES[c] || c}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Contradiction Cards Grid */}
      <div className="contradiction-cards-grid">
        {filteredItems.map((item, idx) => {
          const isConfirmed = item.status === 'confirmed'

          return (
            <article
              key={item.id || idx}
              className={`contradiction-card ${isConfirmed ? 'status-confirmed' : 'status-possible'}`}
            >
              <div className="card-top-bar">
                <span className={`status-pill ${isConfirmed ? 'pill-confirmed' : 'pill-possible'}`}>
                  {isConfirmed ? '🚨 CONFIRMED CONTRADICTION' : '⚠️ POSSIBLE DISCREPANCY'}
                </span>
                <span className="category-tag">
                  {CATEGORY_NAMES[item.category] || item.category}
                </span>
                <span className="confidence-tag">
                  {Math.round((item.confidence || 0.85) * 100)}% confidence
                </span>
              </div>

              <div className="explanation-banner">
                <strong>Legal Inconsistency:</strong> {item.explanation}
              </div>

              {/* Side-by-Side Comparison: Claim A vs Claim B */}
              <div className="side-by-side-comparison">
                {/* Source A */}
                <div className="claim-box box-a">
                  <div className="claim-box-head">
                    <span className="doc-icon">📄</span>
                    <strong className="doc-title">{item.claim_a.source_document}</strong>
                    {item.claim_a.page && <span className="page-tag">p.{item.claim_a.page}</span>}
                  </div>
                  <blockquote className="claim-quote">
                    "{item.claim_a.passage}"
                  </blockquote>
                  {onOpenDocument && (
                    <button
                      className="inspect-doc-link"
                      onClick={() => onOpenDocument(item.claim_a.source_document)}
                    >
                      Inspect Source Record →
                    </button>
                  )}
                </div>

                <div className="versus-divider">
                  <span>VS</span>
                </div>

                {/* Source B */}
                <div className="claim-box box-b">
                  <div className="claim-box-head">
                    <span className="doc-icon">📄</span>
                    <strong className="doc-title">{item.claim_b.source_document}</strong>
                    {item.claim_b.page && <span className="page-tag">p.{item.claim_b.page}</span>}
                  </div>
                  <blockquote className="claim-quote">
                    "{item.claim_b.passage}"
                  </blockquote>
                  {onOpenDocument && (
                    <button
                      className="inspect-doc-link"
                      onClick={() => onOpenDocument(item.claim_b.source_document)}
                    >
                      Inspect Source Record →
                    </button>
                  )}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
