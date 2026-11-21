import { useState, useMemo, useRef, useEffect } from 'react'
import { apiFetch } from '../lib/auth.js'

const API_BASE = import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL || 'http://localhost:8080'

const NODE_COLORS = {
  claim: { bg: 'rgba(59, 130, 246, 0.15)', border: '#3b82f6', text: '#93c5fd', icon: '⚖️' },
  counterclaim: { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', text: '#fca5a5', icon: '🛡️' },
  evidence: { bg: 'rgba(34, 197, 94, 0.15)', border: '#22c55e', text: '#86efac', icon: '📄' },
  witness: { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', text: '#fde68a', icon: '👤' },
  statute: { bg: 'rgba(168, 85, 247, 0.15)', border: '#a855f7', text: '#d8b4fe', icon: '📜' },
  precedent: { bg: 'rgba(99, 102, 241, 0.15)', border: '#6366f1', text: '#c7d2fe', icon: '🏛️' },
  issue: { bg: 'rgba(236, 72, 153, 0.15)', border: '#ec4899', text: '#fbcfe8', icon: '❓' },
  fact: { bg: 'rgba(14, 165, 233, 0.15)', border: '#0ea5e9', text: '#7dd3fc', icon: '📌' },
  date_event: { bg: 'rgba(20, 184, 166, 0.15)', border: '#14b8a6', text: '#99f6e4', icon: '📅' },
  finding: { bg: 'rgba(234, 179, 8, 0.15)', border: '#eab308', text: '#fef08a', icon: '⚡' },
  party: { bg: 'rgba(100, 116, 139, 0.15)', border: '#64748b', text: '#cbd5e1', icon: '👥' },
  argument: { bg: 'rgba(139, 92, 246, 0.15)', border: '#8b5cf6', text: '#c4b5fd', icon: '💬' },
}

const EDGE_COLORS = {
  SUPPORTS: '#22c55e',
  CONTRADICTS: '#ef4444',
  CITES: '#a855f7',
  REBUTS: '#f97316',
  DISTINGUISHES: '#3b82f6',
  OVERRULES: '#dc2626',
  DEPENDS_ON: '#eab308',
  ASSERTED_BY: '#06b6d4',
  SUPPORTED_BY: '#10b981',
  RELATED_TO: '#64748b',
}

export default function EvidenceGraph({ caseId, graphData: propGraphData, onOpenDocument, loading: propLoading = false }) {
  const [internalGraphData, setInternalGraphData] = useState(null)
  const [internalLoading, setInternalLoading] = useState(false)
  const [activeFilter, setActiveFilter] = useState('ALL')
  const [selectedNode, setSelectedNode] = useState(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const containerRef = useRef(null)

  useEffect(() => {
    if (caseId && !propGraphData) {
      setInternalLoading(true)
      apiFetch(`${API_BASE}/cases/${caseId}/evidence-graph`)
        .then((res) => res.json())
        .then((data) => {
          setInternalGraphData(data.graph || data)
        })
        .catch((err) => console.warn('Failed to load evidence graph:', err))
        .finally(() => setInternalLoading(false))
    }
  }, [caseId, propGraphData])

  const graphData = propGraphData || internalGraphData
  const loading = propLoading || internalLoading

  const nodes = useMemo(() => graphData?.nodes || [], [graphData])
  const edges = useMemo(() => graphData?.edges || [], [graphData])

  // Filter nodes based on activeFilter
  const filteredNodes = useMemo(() => {
    if (activeFilter === 'ALL') return nodes
    if (activeFilter === 'CLAIMS') return nodes.filter((n) => n.type === 'claim' || n.type === 'counterclaim')
    if (activeFilter === 'EVIDENCE') return nodes.filter((n) => n.type === 'evidence')
    if (activeFilter === 'WITNESSES') return nodes.filter((n) => n.type === 'witness')
    if (activeFilter === 'STATUTES') return nodes.filter((n) => n.type === 'statute')
    if (activeFilter === 'PRECEDENTS') return nodes.filter((n) => n.type === 'precedent')
    if (activeFilter === 'CONTRADICTIONS') {
      const contraNodeIds = new Set()
      edges.filter((e) => e.relationship === 'CONTRADICTS' || e.relationship === 'REBUTS').forEach((e) => {
        contraNodeIds.add(e.source)
        contraNodeIds.add(e.target)
      })
      return nodes.filter((n) => contraNodeIds.has(n.id))
    }
    return nodes
  }, [nodes, edges, activeFilter])

  const visibleNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes])

  const filteredEdges = useMemo(() => {
    return edges.filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
  }, [edges, visibleNodeIds])

  // Simple deterministic circular/force layout coordinates
  const nodePositions = useMemo(() => {
    const pos = {}
    const count = filteredNodes.length
    if (count === 0) return pos

    const width = 800
    const height = 550
    const centerX = width / 2
    const centerY = height / 2

    // Arrange nodes in concentric rings by importance/type
    filteredNodes.forEach((node, idx) => {
      let radius = 220
      if (node.type === 'issue' || node.type === 'claim') radius = 100
      else if (node.type === 'statute' || node.type === 'precedent') radius = 290
      
      const angle = (idx / count) * 2 * Math.PI
      pos[node.id] = {
        x: centerX + radius * Math.cos(angle) + (idx % 2 === 0 ? 15 : -15),
        y: centerY + radius * Math.sin(angle) * 0.85 + (idx % 3 === 0 ? 10 : -10),
      }
    })
    return pos
  }, [filteredNodes])

  // Mouse pan handlers
  const handleMouseDown = (e) => {
    if (e.target.closest('.graph-node') || e.target.closest('.graph-sidepanel')) return
    setIsPanning(true)
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMove = (e) => {
    if (!isPanning) return
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
  }

  const handleMouseUp = () => setIsPanning(false)

  // Find connected nodes for the active selection
  const connectedInfo = useMemo(() => {
    if (!selectedNode) return []
    const rels = []
    edges.forEach((e) => {
      if (e.source === selectedNode.id) {
        const targetNode = nodes.find((n) => n.id === e.target)
        if (targetNode) rels.push({ relation: e.relationship, target: targetNode, direction: 'outgoing', exp: e.explanation })
      } else if (e.target === selectedNode.id) {
        const sourceNode = nodes.find((n) => n.id === e.source)
        if (sourceNode) rels.push({ relation: e.relationship, target: sourceNode, direction: 'incoming', exp: e.explanation })
      }
    })
    return rels
  }, [selectedNode, edges, nodes])

  if (loading) {
    return (
      <div className="evidence-graph-loading">
        <div className="graph-spinner" />
        <p>Synthesizing Case Evidence & Claim Graph…</p>
        <small>Parsing claims, statutes, citations and factual nexus with strict provenance</small>
      </div>
    )
  }

  if (nodes.length === 0) {
    return (
      <div className="empty-graph-state">
        <span className="empty-icon">🕸️</span>
        <h3>No Evidence Graph Available</h3>
        <p>Upload case documents or re-analyze the case to construct the interactive claim graph.</p>
      </div>
    )
  }

  return (
    <div className="evidence-graph-container">
      {/* Top Controls & Filter Bar */}
      <div className="graph-toolbar">
        <div className="filter-chips">
          {['ALL', 'CLAIMS', 'EVIDENCE', 'WITNESSES', 'STATUTES', 'PRECEDENTS', 'CONTRADICTIONS'].map((f) => (
            <button
              key={f}
              className={`filter-chip ${activeFilter === f ? 'active' : ''}`}
              onClick={() => setActiveFilter(f)}
            >
              {f === 'CONTRADICTIONS' ? '⚠️ Contradictions' : f.charAt(0) + f.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
        <div className="zoom-controls">
          <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))} title="Zoom Out">−</button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))} title="Zoom In">+</button>
          <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }) }} title="Reset View">↺</button>
        </div>
      </div>

      {/* Main SVG Graph Canvas */}
      <div
        ref={containerRef}
        className="graph-canvas-wrapper"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
      >
        <svg
          className="graph-svg"
          viewBox="0 0 800 550"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'center center',
          }}
        >
          <defs>
            {Object.entries(EDGE_COLORS).map(([rel, color]) => (
              <marker
                key={rel}
                id={`arrow-${rel}`}
                viewBox="0 0 10 10"
                refX="22"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill={color} />
              </marker>
            ))}
          </defs>

          {/* Render Edges */}
          <g className="edges-group">
            {filteredEdges.map((e) => {
              const srcPos = nodePositions[e.source]
              const tgtPos = nodePositions[e.target]
              if (!srcPos || !tgtPos) return null

              const isHighlighted = selectedNode && (e.source === selectedNode.id || e.target === selectedNode.id)
              const color = EDGE_COLORS[e.relationship] || '#64748b'

              return (
                <g key={e.id} className="graph-edge-group">
                  <line
                    x1={srcPos.x}
                    y1={srcPos.y}
                    x2={tgtPos.x}
                    y2={tgtPos.y}
                    stroke={color}
                    strokeWidth={isHighlighted ? 2.5 : 1.2}
                    strokeOpacity={isHighlighted ? 1 : 0.6}
                    strokeDasharray={e.relationship === 'CONTRADICTS' ? '5,5' : 'none'}
                    markerEnd={`url(#arrow-${e.relationship})`}
                  />
                  <text
                    x={(srcPos.x + tgtPos.x) / 2}
                    y={(srcPos.y + tgtPos.y) / 2 - 4}
                    fill={color}
                    fontSize="9px"
                    fontWeight="600"
                    textAnchor="middle"
                    className="edge-label"
                  >
                    {e.relationship}
                  </text>
                </g>
              )
            })}
          </g>

          {/* Render Nodes */}
          <g className="nodes-group">
            {filteredNodes.map((n) => {
              const pos = nodePositions[n.id]
              if (!pos) return null

              const isSelected = selectedNode?.id === n.id
              const styling = NODE_COLORS[n.type] || NODE_COLORS.fact

              return (
                <g
                  key={n.id}
                  className={`graph-node ${isSelected ? 'selected' : ''}`}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={(e) => {
                    e.stopPropagation()
                    setSelectedNode(n)
                  }}
                >
                  <circle
                    r={isSelected ? 26 : 22}
                    fill={styling.bg}
                    stroke={styling.border}
                    strokeWidth={isSelected ? 3 : 1.8}
                    className="node-circle"
                  />
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize="13px"
                  >
                    {styling.icon}
                  </text>
                  <text
                    y={32}
                    textAnchor="middle"
                    fill="var(--ink, #1c1812)"
                    fontSize="10.5px"
                    fontWeight={isSelected ? '700' : '500'}
                    className="node-text"
                  >
                    {n.label.length > 20 ? n.label.substring(0, 18) + '…' : n.label}
                  </text>
                </g>
              )
            })}
          </g>
        </svg>
      </div>

      {/* Slide-over Side Panel for Selected Node */}
      {selectedNode && (
        <aside className="graph-sidepanel" aria-label="Node Details">
          <div className="panel-header">
            <div className="node-type-badge" style={{
              background: NODE_COLORS[selectedNode.type]?.bg,
              borderColor: NODE_COLORS[selectedNode.type]?.border,
              color: NODE_COLORS[selectedNode.type]?.text,
            }}>
              <span>{NODE_COLORS[selectedNode.type]?.icon}</span>
              <span>{selectedNode.type.toUpperCase()}</span>
            </div>
            <button className="close-btn" onClick={() => setSelectedNode(null)}>✕</button>
          </div>

          <h3 className="node-title">{selectedNode.label}</h3>

          <div className="provenance-card">
            <span className="prov-label">DOCUMENT PROVENANCE</span>
            <div className="prov-file">
              <span>📄</span>
              <strong>{selectedNode.source_document}</strong>
              {selectedNode.page && <span className="page-pill">Page {selectedNode.page}</span>}
            </div>
            <div className="prov-passage">
              <small>EXTRACTED PASSAGE:</small>
              <p>"{selectedNode.passage}"</p>
            </div>
            <div className="prov-meta">
              <span>Confidence: <strong>{Math.round(selectedNode.confidence * 100)}%</strong></span>
              {onOpenDocument && (
                <button
                  className="view-doc-btn"
                  onClick={() => onOpenDocument(selectedNode.source_document)}
                >
                  View Source Document →
                </button>
              )}
            </div>
          </div>

          {/* Connected Relational Nodes */}
          <div className="connected-nodes-section">
            <span className="section-subtitle">CONNECTED ENTITIES ({connectedInfo.length})</span>
            {connectedInfo.length === 0 ? (
              <p className="no-rels">No explicit relationship edges configured for this entity.</p>
            ) : (
              <div className="rel-list">
                {connectedInfo.map((rel, idx) => (
                  <div
                    key={idx}
                    className="rel-item"
                    onClick={() => setSelectedNode(rel.target)}
                  >
                    <div className="rel-header">
                      <span className="rel-tag" style={{ color: EDGE_COLORS[rel.relation] || '#38bdf8' }}>
                        {rel.direction === 'outgoing' ? '→' : '←'} {rel.relation}
                      </span>
                      <span className="target-type">{rel.target.type}</span>
                    </div>
                    <div className="target-label">{rel.target.label}</div>
                    {rel.exp && <small className="rel-exp">{rel.exp}</small>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  )
}
