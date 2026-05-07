const statusSteps = [
  'Submitting transaction…',
  'Waiting for LLM consensus…',
  'Finalizing score…'
];

export default function RepoInput({
  repoUrl,
  onChange,
  onAnalyze,
  onGetCached,
  loading,
  validationError,
  loadingStep
}) {
  return (
    <section className={`card repo-card ${loading ? 'is-loading' : ''}`}>
      <div className="repo-header">
        <svg viewBox="0 0 16 16" aria-hidden="true" className="branch-icon">
          <path
            fill="currentColor"
            d="M10 2.75a2.75 2.75 0 1 1 4.25 2.3v1.95a2.75 2.75 0 0 1-2.5 2.74v1.51a2.75 2.75 0 1 1-1.5 0V9.74a2.75 2.75 0 0 1-2.5-2.74V5.49A2.75 2.75 0 1 1 9.25 3v4a1.25 1.25 0 0 0 1.25 1.25h1A1.25 1.25 0 0 0 12.75 7V5.05A2.75 2.75 0 0 1 10 2.75Zm1.25 0a1.25 1.25 0 1 0 2.5 0 1.25 1.25 0 0 0-2.5 0Zm-7.5 1a1.25 1.25 0 1 0 0 2.5 1.25 1.25 0 0 0 0-2.5Zm7 8a1.25 1.25 0 1 0 0 2.5 1.25 1.25 0 0 0 0-2.5Z"
          />
        </svg>
        <h2>Analyze Repository</h2>
      </div>
      <p className="repo-subtext">
        Enter a public GitHub repository URL to compute its health score via on-chain LLM
        consensus.
      </p>

      <input
        type="text"
        value={repoUrl}
        onChange={(event) => onChange(event.target.value)}
        className="repo-input"
        placeholder="https://github.com/owner/repo"
      />

      {validationError ? <p className="error-inline">{validationError}</p> : null}

      <div className="repo-actions">
        <button type="button" className="btn-analyze" disabled={loading} onClick={onAnalyze}>
          {loading ? <span className="spinner" aria-label="Loading" /> : 'Analyze'}
        </button>
        <button type="button" className="btn-secondary" disabled={loading} onClick={onGetCached}>
          Get Cached Score
        </button>
      </div>

      {loading ? <p className="status-inline">{statusSteps[loadingStep % statusSteps.length]}</p> : null}
    </section>
  );
}
