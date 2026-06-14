function formatBadgeLabel(value) {
  return String(value).replace(/_/g, ' ');
}

export function StatusBadge({ value }) {
  if (!value) return '—';
  return (
    <span className={`badge badge-status badge-${String(value).toLowerCase()}`}>
      {formatBadgeLabel(value)}
    </span>
  );
}

export function PriorityBadge({ value }) {
  if (!value) return '—';
  return (
    <span className={`badge badge-priority badge-${String(value).toLowerCase()}`}>
      {formatBadgeLabel(value)}
    </span>
  );
}

export function SentimentBadge({ value }) {
  if (!value) return '—';
  return (
    <span className={`badge badge-sentiment badge-${String(value).toLowerCase()}`}>
      {formatBadgeLabel(value)}
    </span>
  );
}

export function renderDetailValue(field) {
  if (field.badge === 'status') return <StatusBadge value={field.value} />;
  if (field.badge === 'priority') return <PriorityBadge value={field.value} />;
  if (field.badge === 'sentiment') return <SentimentBadge value={field.value} />;
  return field.value;
}
