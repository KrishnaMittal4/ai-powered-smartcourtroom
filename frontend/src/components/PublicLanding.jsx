import ParticleBackground from './ParticleBackground.jsx'

export default function PublicLanding({ onRequireAuth, onSignIn, onCreateAccount }) {
  const gate = (action) => () => onRequireAuth(action)

  return (
    <div className="public-shell">
      <ParticleBackground />
      <header className="public-topbar">
        <div className="public-brand">
          <div className="public-mark">⚖</div>
          <div>
            <b>LEXAI</b>
            <small>LEGAL INTELLIGENCE · VERIFIED EVIDENCE</small>
          </div>
        </div>
        <div className="public-auth-actions">
          <button className="btn-quiet" onClick={onSignIn}>Sign in</button>
          <button className="btn-primary" onClick={onCreateAccount}>Create account</button>
        </div>
      </header>

      <main className="public-main">
        <section className="public-hero">
          <span className="hero-eyebrow">⚖ INDIAN LEGAL INTELLIGENCE SYSTEM</span>
          <h1>
            Research. Verify.<br />
            Argue. <em>Decide.</em>
          </h1>
          <p>
            Evidence-grounded legal intelligence for Indian law, powered by hybrid retrieval, verified citations, and agentic courtroom simulation.
          </p>

          {/* Architecture & Trust Badges */}
          <div className="public-badges">
            <span>● Hybrid RAG (FAISS + BM25)</span>
            <span>● Verified Citations & Grounds</span>
            <span>● Corrective RAG (CRAG)</span>
            <span>● Private Case Workspaces</span>
            <span>● Multi-Agent Moot Court</span>
          </div>

          {/* Primary Action Tools */}
          <div className="public-tools">
            <button className="public-primary-upload" onClick={gate('upload')}>
              <strong>📄 Start Legal Research</strong>
              <small>Upload judgment, court order or case dossier · private indexing · page-level citation verification.</small>
              <b>Upload & Research →</b>
            </button>
            <button onClick={gate('moot')}>
              <strong>⚖ Moot Court</strong>
              <small>Practice arguments in 5 modes: Step in as Counsel or Judge against an adversarial AI Bench.</small>
              <b>Try Moot Court →</b>
            </button>
            <button onClick={gate('draft')}>
              <strong>✎ Legal Drafting & BNS</strong>
              <small>BNS ↔ IPC transition analysis, notice scanner, and automated legal draft generator.</small>
              <b>Start Drafting →</b>
            </button>
          </div>

          {/* 6 Capabilities Matrix */}
          <div className="public-capabilities-grid">
            <div className="public-capability-card" onClick={gate('cases')}>
              <div className="cap-header">
                <span className="cap-icon">🕸️</span>
                <span className="cap-tag">CASE INTELLIGENCE</span>
              </div>
              <h3>Evidence & Claim Graph</h3>
              <p>Extracts legal issues, facts, witness statements, and statutes into an interactive relational graph with full source provenance.</p>
            </div>

            <div className="public-capability-card" onClick={gate('upload')}>
              <div className="cap-header">
                <span className="cap-icon">🎯</span>
                <span className="cap-tag">CALIBRATED RAG</span>
              </div>
              <h3>Adaptive Confidence Engine</h3>
              <p>Calibrates dense similarity, BM25, and Cross-Encoder logits into verified confidence actions with safe refusal fallback.</p>
            </div>

            <div className="public-capability-card" onClick={gate('moot')}>
              <div className="cap-header">
                <span className="cap-icon">🏛️</span>
                <span className="cap-tag">ADVERSARIAL TRIAL</span>
              </div>
              <h3>Interactive Moot Court</h3>
              <p>Speech-to-text dictation, real-time courtroom objections, chess clock timer, and an 8-category judicial scorecard.</p>
            </div>

            <div className="public-capability-card" onClick={gate('cases')}>
              <div className="cap-header">
                <span className="cap-icon">⏱️</span>
                <span className="cap-tag">CHRONOLOGY</span>
              </div>
              <h3>Automatic Case Timeline</h3>
              <p>Chronological legal milestones from FIRs to judgments with automated multi-document Date Conflict alerts.</p>
            </div>

            <div className="public-capability-card" onClick={gate('cases')}>
              <div className="cap-header">
                <span className="cap-icon">⚡</span>
                <span className="cap-tag">NLI VERIFICATION</span>
              </div>
              <h3>Cross-Document Contradictions</h3>
              <p>Side-by-side comparison of conflicting witness statements, dates, and amounts with exact verbatim exhibit quotes.</p>
            </div>

            <div className="public-capability-card" onClick={gate('draft')}>
              <div className="cap-header">
                <span className="cap-icon">⚖️</span>
                <span className="cap-tag">INDIAN LAW SUITE</span>
              </div>
              <h3>BNS Lens & Legal Drafting</h3>
              <p>Instant Bharatiya Nyaya Sanhita transition lookup and automated drafting of legal notices, petitions, and replies.</p>
            </div>
          </div>

          {/* Security & Privacy Notice */}
          <section className="public-privacy">
            <div>🔒</div>
            <div>
              <b>Your case files belong to your private workspace.</b>
              <p>Sign in before uploading. LEXAI keeps case ownership strictly isolated to your account and verifies answers against uploaded evidence.</p>
            </div>
          </section>
        </section>
      </main>
    </div>
  )
}
