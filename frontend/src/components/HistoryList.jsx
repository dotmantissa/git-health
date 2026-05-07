function scoreColorClass(score) {
  if (score >= 70) return 'c-green';
  if (score >= 40) return 'c-yellow';
  return 'c-red';
}

export default function HistoryList({ history, onSelect }) {
  return (
    <section className="history-wrap">
      <p className="history-title">This Session</p>

      {history.length === 0 ? (
        <p className="history-empty">No analyses yet this session</p>
      ) : (
        <div>
          {history.map((item, index) => {
            const colorClass = scoreColorClass(item.score);
            return (
              <button
                key={`${item.url}-${item.timestamp}-${index}`}
                type="button"
                className="history-row"
                onClick={() => onSelect(item)}
              >
                <span className={`history-dot ${colorClass}`} />
                <span className="history-url" title={item.url}>{item.url}</span>
                <span className={`history-score ${colorClass}`}>{item.score}</span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
