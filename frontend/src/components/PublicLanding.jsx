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
            <b>LEXAI SMART COURTROOM</b>
            <small>LEGAL INTELLIGENCE OPERATING SYSTEM</small>
          </div>
        </div>
        <div className="public-auth-actions">
          <button className="btn-quiet" onClick={onSignIn}>Sign in</button>
          <button className="btn-primary" onClick={onCreateAccount}>Create account</button>
        </div>
      </header>

      <main className="public-main">
        <section className="public-hero">
          <div className="hero-eyebrow-chip">
            <span className="chip-pulse" />
            <span>INDIAN JURISPRUDENCE · MULTI-AGENT TRIAL SIMULATION</span>
          </div>

          <h1 className="hero-headline">
            Research. Verify.<br />
            Argue. <em>Decide.</em>
          </h1>

          <p className="hero-subheading">
            Evidence-grounded legal intelligence for Indian law, powered by hybrid retrieval, verified citations, and agentic courtroom simulation.
          </p>

          <div className="public-cta-group">
            <button className="btn-hero-primary" onClick={gate('upload')}>
              <span>📄 Start Legal Research</span>
              <small>Upload judgment or case dossier →</small>
            </button>
            <button className="btn-hero-secondary" onClick={gate('moot')}>
              <span>⚖️ Open Moot Court</span>
              <small>5-Mode Human vs AI courtroom</small>
            </button>
          </div>

          {/* Architecture / Trust Strip */}
          <div className="architecture-trust-strip" aria-label="System Capabilities">
            <div className="trust-pill">
              <span className="trust-dot blue" />
              <span>Hybrid RAG (FAISS + BM25)</span>
            </div>
            <div className="trust-pill">
              <span className="trust-dot green" />
              <span>Verified Citations & Grounds</span>
            </div>
            <div className="trust-pill">
              <span className="trust-dot purple" />
              <span>Corrective RAG (CRAG)</span>
            </div>
            <div className="trust-pill">
              <span className="trust-dot gold" />
              <span>Private Case Workspaces</span>
            </div>
            <div className="trust-pill">
              <span className="trust-dot red" />
              <span>Multi-Agent Courtroom</span>
            </div>
          </div>

          {/* Core Feature Matrix */}
          <div className="feature-showcase-grid">
            <div className="showcase-card" onClick={gate('cases')}>
              <div className="card-top">
                <span className="card-icon">🕸️</span>
                <span className="card-tag">Case Intelligence</span>
              </div>
              <h3>Evidence & Claim Graph</h3>
              <p>Extracts legal issues, facts, witness testimonies, and statutory provisions into an interactive SVG knowledge graph with full source provenance.</p>
            </div>

            <div className="showcase-card" onClick={gate('upload')}>
              <div className="card-top">
                <span className="card-icon">🎯</span>
                <span className="card-tag">Calibrated RAG</span>
              </div>
              <h3>Adaptive Confidence Engine</h3>
              <p>Combines dense FAISS, BM25, and Cross-Encoder sigmoid calibration into verified high/medium/low confidence signals with safe refusal fallback.</p>
            </div>

            <div className="showcase-card" onClick={gate('moot')}>
              <div className="card-top">
                <span className="card-icon">🏛️</span>
                <span className="card-tag">Adversarial Trial</span>
              </div>
              <h3>Interactive Moot Court</h3>
              <p>Step in as Petitioner, Respondent, or Judge. Real-time courtroom speech dictation, live objections, and an 8-category judicial scorecard.</p>
            </div>

            <div className="showcase-card" onClick={gate('cases')}>
              <div className="card-top">
                <span className="card-icon">⏱️</span>
                <span className="card-tag">Chronology</span>
              </div>
              <h3>Automatic Case Timeline</h3>
              <p>Automated extraction of FIRs, notices, arrests, and hearings. Disagreements between documents are automatically flagged as Date Conflicts.</p>
            </div>

            <div className="showcase-card" onClick={gate('cases')}>
              <div className="card-top">
                <span className="card-icon">⚡</span>
                <span className="card-tag">NLI Verification</span>
              </div>
              <h3>Cross-Document Contradictions</h3>
              <p>Semantic contradiction detector compares witness claims, dates, and amounts side-by-side with exact verbatim exhibit quotes.</p>
            </div>

            <div className="showcase-card" onClick={gate('draft')}>
              <div className="card-top">
                <span className="card-icon">⚖️</span>
                <span className="card-tag">Indian Law Suite</span>
              </div>
              <h3>BNS Lens & Legal Drafting</h3>
              <p>Instant Bharatiya Nyaya Sanhita ↔ IPC mapping and automated drafting of legal notices, bail applications, and writ petitions.</p>
            </div>
          </div>

          {/* Security & Privacy Banner */}
          <section className="public-privacy">
            <div className="lock-icon-wrap">🔒</div>
            <div>
              <b>Strict Case Isolation & Evidentiary Privacy</b>
              <p>Uploaded documents are encrypted and segregated to your private workspace. LexAI never leaks case facts or reasoning outside your authenticated session.</p>
            </div>
          </section>
        </section>
      </main>
    </div>
  )
}
