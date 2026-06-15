import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAnalyticsSummary } from '../api/api.js';
import './Dashboard.css';

const METRIC_DEFINITIONS = [
  { label: 'Total Tickets', keys: ['total_tickets', 'totalTickets', 'total'] },
  { label: 'Open Tickets', keys: ['open_tickets', 'openTickets', 'open'] },
  { label: 'In Progress Tickets', keys: ['in_progress_tickets', 'inProgressTickets', 'in_progress'] },
  { label: 'Resolved Tickets', keys: ['resolved_tickets', 'resolvedTickets', 'resolved'] },
  { label: 'Closed Tickets', keys: ['closed_tickets', 'closedTickets', 'closed'] },
  { label: 'High Priority Tickets', keys: ['high_priority_tickets', 'highPriorityTickets', 'high_priority'] },
  { label: 'Urgent Tickets', keys: ['urgent_tickets', 'urgentTickets', 'urgent'] },
  {
    label: 'Negative Sentiment Tickets',
    keys: ['negative_sentiment_tickets', 'negativeSentimentTickets', 'negative_sentiment'],
  },
  { label: 'AI Accuracy', keys: ['ai_accuracy', 'aiAccuracy'], format: 'percent' },
  { label: 'Resolution Rate', keys: ['resolution_rate', 'resolutionRate'], format: 'percent' },
];

function getErrorMessage(error) {
  const detail = error.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ');
  }

  return 'Failed to load dashboard summary.';
}

function getFieldValue(data, keys) {
  if (!data) return undefined;

  for (const key of keys) {
    if (data[key] !== undefined && data[key] !== null) {
      return data[key];
    }
  }

  return undefined;
}

function formatMetricValue(value, format) {
  if (value === undefined || value === null) {
    return '—';
  }

  if (format === 'percent') {
    return `${Number(value).toFixed(1)}%`;
  }

  return value;
}

function Dashboard() {
  const isAdmin = localStorage.getItem('role') === 'ADMIN';
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(isAdmin);
  const [error, setError] = useState('');

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getAnalyticsSummary();
      setSummary(response.data);
    } catch (err) {
      setSummary(null);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchSummary();
    }
  }, [fetchSummary, isAdmin]);

  const metricCards = useMemo(
    () =>
      METRIC_DEFINITIONS.map((metric) => ({
        label: metric.label,
        value: formatMetricValue(getFieldValue(summary, metric.keys), metric.format),
      })),
    [summary],
  );

  if (!isAdmin) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-access-denied">
          <h1>Access Denied</h1>
          <p>The dashboard is available to administrators only.</p>
          <Link to="/tickets" className="dashboard-action-button dashboard-action-primary">
            Go to Tickets
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <div>
          <h1>Admin Dashboard</h1>
          <p className="dashboard-subtitle">
            Monitor ticket volume, priority, sentiment, and resolution progress.
          </p>
        </div>
        <button type="button" className="dashboard-refresh" onClick={fetchSummary} disabled={loading}>
          Refresh
        </button>
      </div>

      <section className="dashboard-actions">
        <Link to="/tickets" className="dashboard-action-button dashboard-action-secondary">
          View Tickets
        </Link>
        <Link to="/analytics" className="dashboard-action-button dashboard-action-secondary">
          View Analytics
        </Link>
        <Link to="/create-ticket" className="dashboard-action-button dashboard-action-primary">
          Create Ticket
        </Link>
      </section>

      {loading && <p className="dashboard-message">Loading dashboard...</p>}
      {!loading && error && <p className="dashboard-error">{error}</p>}

      {!loading && !error && summary && (
        <section className="dashboard-cards">
          {metricCards.map((card) => (
            <article key={card.label} className="dashboard-card">
              <span className="dashboard-card-label">{card.label}</span>
              <strong className="dashboard-card-value">{card.value}</strong>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

export default Dashboard;
