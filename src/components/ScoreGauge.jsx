function getScoreMeta(score) {
  if (score >= 70) {
    return {
      label: 'Healthy',
      color: 'var(--accent-green)',
      badgeClass: 'badge-healthy',
      text: 'Recent maintenance and issue load suggest this repository is actively healthy.'
    };
  }
  if (score >= 40) {
    return {
      label: 'Fair',
      color: 'var(--accent-yellow)',
      badgeClass: 'badge-fair',
      text: 'Repository activity is moderate. Review maintenance cadence and issue backlog.'
    };
  }
  return {
    label: 'At Risk',
    color: 'var(--accent-red)',
    badgeClass: 'badge-risk',
    text: 'Signals indicate stale maintenance or high open-issue pressure.'
  };
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleString();
}

export default function ScoreGauge({ entry }) {
  if (!entry) return null;

  const score = Math.max(0, Math.min(100, Number(entry.score) || 0));
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const meta = getScoreMeta(score);

  return (
    <section className="card gauge-card">
      <div className="gauge-layout">
        <div className="gauge-wrap">
          <svg width="200" height="200" viewBox="0 0 200 200" className="gauge-svg">
            <circle cx="100" cy="100" r={radius} stroke="var(--border)" strokeWidth="14" fill="none" />
            <circle
              cx="100"
              cy="100"
              r={radius}
              stroke={meta.color}
              strokeWidth="14"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform="rotate(-90 100 100)"
              className="score-arc"
            />
            <text x="100" y="103" textAnchor="middle" className="gauge-score" fill={meta.color}>
              {score}
            </text>
            <text x="100" y="126" textAnchor="middle" className="gauge-scale">
              /100
            </text>
          </svg>
        </div>

        <div className="gauge-details">
          <p className="repo-url" title={entry.url}>{entry.url}</p>
          <span className={`score-badge ${meta.badgeClass}`}>{meta.label}</span>
          <p className="score-text">{meta.text}</p>
          <p className="score-time">Analyzed at {formatTime(entry.timestamp)}</p>
        </div>
      </div>
      <details style={{ marginTop: '1rem' }}>
        <summary>Fetched Contract Data (Debug)</summary>
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {JSON.stringify(entry.details || {}, null, 2)}
        </pre>
      </details>
    </section>
  );
}
