import { PriorityBadge, SentimentBadge, StatusBadge } from './badges.jsx';

export function renderDetailValue(field) {
  if (field.badge === 'status') return <StatusBadge value={field.value} />;
  if (field.badge === 'priority') return <PriorityBadge value={field.value} />;
  if (field.badge === 'sentiment') return <SentimentBadge value={field.value} />;
  return field.value;
}
