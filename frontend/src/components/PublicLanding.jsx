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

          {/* Primary Intake Hero Zone */}
          <div className="hero-intake-card" onClick={gate('upload')}>
            <div className="intake-badge-pill">
              <span>⚖️ SECURE CASE DOSSIER INTAKE</span>
            </div>
            <div className="intake-body">
              <div className="intake-icon-wrap">📄</div>
              <div className="intake-text">
                <h2>Upload Case Document or Court Judgment (PDF)</h2>
                <p>
                  Drag & drop FIR, chargesheet, petition, deposition, or contract · Private indexing with page-level citation & evidence verification.
                </p>
              </div>
            </div>
            <div className="intake-actions-bar">
              <button type="button" className="btn-intake-primary">
                <span>Browse Case Files</span>
                <span className="btn-arrow">→</span>
              </button>
            </div>
          </div>

          {/* Two Quick Action Pillars */}
          <div className="hero-quick-pillars">
            <button type="button" className="quick-pillar-btn pillar-moot" onClick={gate('moot')}>
              <div className="pillar-icon">🏛️</div>
              <div className="pillar-info">
                <strong>Launch Moot Court Arena</strong>
                <small>5 adversarial trial modes: Petitioner, Respondent & Judge against AI Bench.</small>
              </div>
              <span className="pillar-arrow">Try Courtroom →</span>
            </button>
            <button type="button" className="quick-pillar-btn pillar-bns" onClick={gate('draft')}>
              <div className="pillar-icon">⚖️</div>
              <div className="pillar-info">
                <strong>BNS ↔ IPC Lens & Legal Drafting</strong>
                <small>Compare 2024 New Criminal Laws, scan notice clauses, and draft petitions.</small>
              </div>
              <span className="pillar-arrow">Explore Tools →</span>
            </button>
          </div>

          {/* 6 Differentiated Capabilities Matrix (Category Colors & Hover Glow) */}
          <div className="public-capabilities-grid">
            {/* 1. Evidence Graph */}
            <div className="public-capability-card card-emerald" onClick={gate('cases')}>
              <div className="cap-header">
                <span className="cap-icon">🕸️</span>
                <span className="cap-tag tag-emerald">CASE INTELLIGENCE</span>
              </div>
              <h3>Evidence & Claim Graph</h3>
              <p>Extracts legal issues, facts, witness statements, and statutes into an interactive relational graph with full source provenance.</p>
              <span className="cap-footer-link link-emerald">Explore Knowledge Graph →</span>
            </div>

            {/* 2. Adaptive Confidence */}
            <div className="public-capability-card card-amber" onClick={gate('upload')}>
              <div className="cap-header">
                <span className="cap-icon">🎯</span>
                <span className="cap-tag tag-amber">CALIBRATED RAG</span>
              </div>
              <h3>Adaptive Confidence Engine</h3>
              <p>Calibrates dense similarity, BM25, and Cross-Encoder logits into verified confidence actions with safe refusal fallback.</p>
              <span className="cap-footer-link link-amber">View Retrieval Signals →</span>
            </div>

            {/* 3. Moot Court */}
            <div className="public-capability-card card-blue" onClick={gate('moot')}>
              <div className="cap-header">
                <span className="cap-icon">🏛️</span>
                <span className="cap-tag tag-blue">ADVERSARIAL TRIAL</span>
              </div>
              <h3>Interactive Moot Court</h3>
              <p>Speech-to-text dictation, real-time courtroom objections, chess clock timer, and an 8-category judicial scorecard.</p>
              <span className="cap-footer-link link-blue">Step In As Counsel / Judge →</span>
            </div>

            {/* 4. Timeline */}
            <div className="public-capability-card card-cyan" onClick={gate('cases')}>
              <div className="cap-header">
                <span className="cap-icon">⏱️</span>
                <span className="cap-tag tag-cyan">CHRONOLOGY</span>
              </div>
              <h3>Automatic Case Timeline</h3>
              <p>Chronological legal milestones from FIRs to judgments with automated multi-document Date Conflict alerts.</p>
              <span className="cap-footer-link link-cyan">Detect Milestone Conflicts →</span>
            </div>

            {/* 5. Contradictions */}
            <div className="public-capability-card card-crimson" onClick={gate('cases')}>
              <div className="cap-header">
                <span className="cap-icon">⚡</span>
                <span className="cap-tag tag-crimson">NLI VERIFICATION</span>
              </div>
              <h3>Cross-Document Contradictions</h3>
              <p>Side-by-side comparison of conflicting witness statements, dates, and amounts with exact verbatim exhibit quotes.</p>
              <span className="cap-footer-link link-crimson">Compare Verbatim Quotes →</span>
            </div>

            {/* 6. BNS & Drafting */}
            <div className="public-capability-card card-purple" onClick={gate('draft')}>
              <div className="cap-header">
                <span className="cap-icon">⚖️</span>
                <span className="cap-tag tag-purple">INDIAN LAW SUITE</span>
              </div>
              <h3>BNS Lens & Legal Drafting</h3>
              <p>Instant Bharatiya Nyaya Sanhita transition lookup and automated drafting of legal notices, petitions, and replies.</p>
              <span className="cap-footer-link link-purple">Map Laws & Generate Drafts →</span>
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

          {/* Reserved Rights Copyright Footer */}
          <footer className="public-footer-copyright">
            <div className="copyright-line">
              © 2026 Krishna Mittal. All Rights Reserved.
            </div>
            <div className="copyright-subline">
              AI-Powered Smart Courtroom
            </div>
          </footer>
        </section>
      </main>
    </div>
  )
}
