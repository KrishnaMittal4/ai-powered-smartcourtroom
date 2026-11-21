import { useState, useMemo } from 'react'

const EVENT_BADGES = {
  incident: { label: 'Incident', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.12)', icon: '⚡' },
  complaint: { label: 'Complaint', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.12)', icon: '📝' },
  fir: { label: 'FIR', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)', icon: '🚨' },
  arrest: { label: 'Arrest', color: '#dc2626', bg: 'rgba(220, 38, 38, 0.12)', icon: '🔒' },
  notice: { label: 'Notice', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.12)', icon: '📬' },
  investigation: { label: 'Investigation', color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.12)', icon: '🔍' },
  evidence_collection: { label: 'Evidence', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)', icon: '📦' },
  chargesheet: { label: 'Chargesheet', color: '#d97706', bg: 'rgba(217, 119, 6, 0.12)', icon: '📑' },
  hearing: { label: 'Hearing', color: '#6366f1', bg: 'rgba(99, 102, 241, 0.12)', icon: '⚖️' },
  order: { label: 'Order', color: '#a855f7', bg: 'rgba(168, 85, 247, 0.12)', icon: '📜' },
  judgment: { label: 'Judgment', color: '#eab308', bg: 'rgba(234, 179, 8, 0.12)', icon: '🏛️' },
  appeal: { label: 'Appeal', color: '#ec4899', bg: 'rgba(236, 72, 153, 0.12)', icon: '↗️' },
  deadline: { label: 'Deadline', color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.12)', icon: '⏳' },
  other: { label: 'Milestone', color: '#64748b', bg: 'rgba(100, 116, 139, 0.12)', icon: '📌' },
}

export default function CaseTimeline({ timelineData, onOpenDocument, loading = false }) {
  const [filter, setFilter] = useState('ALL')
  const [isAscending, setIsAscending] = useState(true)
  const [selectedEvent, setSelectedEvent] = useState(null)

  const rawEvents = useMemo(() => timelineData?.events || [], [timelineData])
  const conflictCount = useMemo(() => timelineData?.conflict_count || 0, [timelineData])

  const filteredEvents = useMemo(() => {
    let list = [...rawEvents]
    if (filter !== 'ALL') {
      if (filter === 'INCIDENT') list = list.filter((e) => e.event_type === 'incident')
      else if (filter === 'POLICE') list = list.filter((e) => ['fir', 'arrest', 'investigation', 'chargesheet'].includes(e.event_type))
      else if (filter === 'EVIDENCE') list = list.filter((e) => ['evidence_collection', 'notice'].includes(e.event_type))
      else if (filter === 'COURT') list = list.filter((e) => ['complaint', 'hearing', 'order', 'judgment', 'appeal'].includes(e.event_type))
      else if (filter === 'DEADLINES') list = list.filter((e) => e.event_type === 'deadline')
    }

    list.sort((a, b) => {
      const d1 = a.date_normalized || '9999-99-99'
      const d2 = b.date_normalized || '9999-99-99'
      return isAscending ? d1.localeCompare(d2) : d2.localeCompare(d1)
    })
    return list
  }, [rawEvents, filter, isAscending])

  if (loading) {
    return (
      <div className="timeline-loading">
        <div className="graph-spinner" />
        <p>Extracting Chronological Case Timeline…</p>
        <small>Scanning procedural dates, police filings, notices and detecting date discrepancies</small>
      </div>
    )
  }

  if (rawEvents.length === 0) {
    return (
      <div className="empty-graph-state">
        <span className="empty-icon">📅</span>
        <h3>No Timeline Milestones Extracted</h3>
        <p>Upload case documents or re-analyze the case to generate the chronological event timeline.</p>
      </div>
    )
  }

  return (
    <div className="case-timeline-container">
      {/* Date Conflict Banner */}
      {conflictCount > 0 && (
        <div className="date-conflict-alert" role="alert">
          <span className="alert-icon">⚠️</span>
          <div className="alert-content">
            <strong>{conflictCount} Date Conflict{conflictCount > 1 ? 's' : ''} Flagged Across Documents</strong>
            <p>Multiple uploaded records report conflicting dates for identical procedural milestones. Verify against original certified copies.</p>
          </div>
        </div>
      )}

      {/* Toolbar & Filters */}
      <div className="timeline-toolbar">
        <div className="filter-chips">
          {[
            { id: 'ALL', label: 'All Milestones' },
            { id: 'INCIDENT', label: 'Incidents' },
            { id: 'POLICE', label: 'Police / FIR' },
            { id: 'EVIDENCE', label: 'Evidence / Notices' },
            { id: 'COURT', label: 'Court & Orders' },
            { id: 'DEADLINES', label: 'Deadlines' },
          ].map((f) => (
            <button
              key={f.id}
              className={`filter-chip ${filter === f.id ? 'active' : ''}`}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <button
          className="order-toggle-btn"
          onClick={() => setIsAscending((prev) => !prev)}
          title="Toggle Chronological Direction"
        >
          <span>{isAscending ? '↓ Earliest to Latest' : '↑ Latest to Earliest'}</span>
        </button>
      </div>

      {/* Vertical Interactive Timeline */}
      <div className="timeline-vertical-track">
        {filteredEvents.map((ev, idx) => {
          const badge = EVENT_BADGES[ev.event_type] || EVENT_BADGES.other
          const isSelected = selectedEvent?.id === ev.id

          return (
            <div
              key={ev.id || idx}
              className={`timeline-entry ${ev.has_conflict ? 'has-conflict' : ''} ${isSelected ? 'selected' : ''}`}
              onClick={() => setSelectedEvent(ev)}
            >
              <div className="timeline-node-marker" style={{ borderColor: badge.color, background: badge.bg }}>
                <span>{badge.icon}</span>
              </div>

              <div className="timeline-card">
                <div className="timeline-card-head">
                  <div className="date-display">
                    <span className="event-date">{ev.date}</span>
                    {ev.date_normalized && ev.date_normalized !== '9999-99-99' && (
                      <small className="date-iso">({ev.date_normalized})</small>
                    )}
                  </div>
                  <span
                    className="event-badge"
                    style={{ color: badge.color, background: badge.bg, borderColor: badge.color }}
                  >
                    {badge.label}
                  </span>
                </div>

                <h4 className="event-title">{ev.title}</h4>
                <p className="event-desc">{ev.description}</p>

                {ev.has_conflict && (
                  <div className="conflict-badge">
                    <span>⚠️</span>
                    <span>{ev.conflict_details || 'DATE CONFLICT: Differing dates reported in case records'}</span>
                  </div>
                )}

                <div className="event-provenance-row">
                  <span className="source-doc">
                    📄 {ev.source_document} {ev.page ? `· p.${ev.page}` : ''}
                  </span>
                  <span className="confidence-pill">
                    {Math.round((ev.confidence || 0.85) * 100)}% confidence
                  </span>
                  {onOpenDocument && (
                    <button
                      className="inline-doc-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        onOpenDocument(ev.source_document)
                      }}
                    >
                      View Source →
                    </button>
                  )}
                </div>

                {/* Excerpt Accordion if Selected */}
                {isSelected && ev.source_text && (
                  <div className="event-passage-drawer">
                    <small>VERBATIM SOURCE RECORD:</small>
                    <p>"{ev.source_text}"</p>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
