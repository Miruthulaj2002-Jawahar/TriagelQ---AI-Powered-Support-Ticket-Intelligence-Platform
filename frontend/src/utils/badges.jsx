import { formatBadgeLabel } from './badgeHelpers.js';

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
