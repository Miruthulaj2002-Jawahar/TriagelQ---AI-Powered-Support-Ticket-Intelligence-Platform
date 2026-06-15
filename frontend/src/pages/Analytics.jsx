import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getAnalyticsSummary } from '../api/api.js';
import './Analytics.css';

const METRIC_DEFINITIONS = [
  { label: 'Total Tickets', keys: ['total_tickets', 'totalTickets', 'total'] },
  { label: 'Open', keys: ['open_tickets', 'openTickets', 'open'] },
  { label: 'In Progress', keys: ['in_progress_tickets', 'inProgressTickets', 'in_progress'] },
  { label: 'Resolved', keys: ['resolved_tickets', 'resolvedTickets', 'resolved'] },
  { label: 'Closed', keys: ['closed_tickets', 'closedTickets', 'closed'] },
  { label: 'Urgent', keys: ['urgent_tickets', 'urgentTickets', 'urgent'] },
  { label: 'High Priority', keys: ['high_priority_tickets', 'highPriorityTickets', 'high_priority'] },
  {
    label: 'Negative Sentiment',
    keys: ['negative_sentiment_tickets', 'negativeSentimentTickets', 'negative_sentiment'],
  },
  { label: 'Resolution Rate', keys: ['resolution_rate', 'resolutionRate'], format: 'percent' },
];

const AI_METRIC_DEFINITIONS = [
  { label: 'AI Accuracy', keys: ['ai_accuracy', 'aiAccuracy'], format: 'percent' },
  { label: 'Manual Override Rate', keys: ['override_rate', 'overrideRate'], format: 'percent' },
  { label: 'Overridden Tickets', keys: ['overridden_ticket_count', 'overriddenTickets'] },
  { label: 'Accepted AI Count', keys: ['accepted_ai_count', 'acceptedAiCount'] },
  { label: 'Classified Tickets', keys: ['total_classified_tickets', 'totalClassifiedTickets'] },
];

const GROUPED_DATA_DEFINITIONS = [
  { title: 'Tickets by Status', keys: ['tickets_by_status', 'ticketsByStatus', 'by_status'] },
  { title: 'Tickets by Priority', keys: ['tickets_by_priority', 'ticketsByPriority', 'by_priority'] },
  { title: 'Tickets by Category', keys: ['tickets_by_category', 'ticketsByCategory', 'by_category'] },
  { title: 'Tickets by Sentiment', keys: ['tickets_by_sentiment', 'ticketsBySentiment', 'by_sentiment'] },
];

function getErrorMessage(error) {
  const detail = error.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ');
  }

  return 'Failed to load analytics summary.';
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

function dictToChartData(record) {
  if (!record || typeof record !== 'object') {
    return [];
  }

  return Object.entries(record).map(([name, value]) => ({
    name,
    value: Number(value) || 0,
  }));
}

function AnalyticsChart({ title, data }) {
  if (!data.length) {
    return null;
  }

  return (
    <section className="analytics-chart-panel">
      <h2>{title}</h2>
      <div className="analytics-chart-container">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="name"
              tick={{ fill: 'var(--text)', fontSize: 12 }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={{ stroke: 'var(--border)' }}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: 'var(--text)', fontSize: 12 }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={{ stroke: 'var(--border)' }}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--code-bg)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                color: 'var(--text-h)',
              }}
              labelStyle={{ color: 'var(--text-h)' }}
            />
            <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function Analytics() {
  const role = localStorage.getItem('role');
  const isAdmin = role === 'ADMIN';

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
    if (!isAdmin) {
      return undefined;
    }
    const frameId = requestAnimationFrame(() => {
      fetchSummary();
    });
    return () => cancelAnimationFrame(frameId);
  }, [fetchSummary, isAdmin]);

  const metricCards = useMemo(
    () =>
      METRIC_DEFINITIONS.map((metric) => ({
        label: metric.label,
        value: formatMetricValue(getFieldValue(summary, metric.keys), metric.format),
      })),
    [summary],
  );

  const aiMetricCards = useMemo(
    () =>
      AI_METRIC_DEFINITIONS.map((metric) => ({
        label: metric.label,
        value: formatMetricValue(getFieldValue(summary, metric.keys), metric.format),
      })),
    [summary],
  );

  const chartSections = useMemo(
    () =>
      GROUPED_DATA_DEFINITIONS.map((section) => ({
        title: section.title,
        data: dictToChartData(getFieldValue(summary, section.keys)),
      })).filter((section) => section.data.length > 0),
    [summary],
  );

  const aiClassificationChart = useMemo(
    () => dictToChartData(getFieldValue(summary, ['ai_classification_summary', 'aiClassificationSummary'])),
    [summary],
  );

  if (!isAdmin) {
    return (
      <div className="analytics-page">
        <div className="analytics-access-denied">
          <h1>Access Denied</h1>
          <p>Analytics is available to administrators only.</p>
          <Link to="/tickets" className="analytics-link-button">
            Go to Tickets
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      <div className="analytics-header">
        <div>
          <h1>Analytics Dashboard</h1>
          <p className="analytics-subtitle">Ticket metrics and trends for administrators</p>
        </div>
        <button type="button" className="analytics-refresh" onClick={fetchSummary} disabled={loading}>
          Refresh
        </button>
      </div>

      {loading && <p className="analytics-message">Loading analytics...</p>}
      {!loading && error && <p className="analytics-error">{error}</p>}

      {!loading && !error && summary && (
        <>
          <section className="analytics-section">
            <h2>AI Classification Metrics</h2>
            <div className="analytics-cards">
              {aiMetricCards.map((card) => (
                <article key={card.label} className="analytics-card">
                  <span className="analytics-card-label">{card.label}</span>
                  <strong className="analytics-card-value">{card.value}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="analytics-section">
            <h2>Ticket Overview</h2>
            <div className="analytics-cards">
              {metricCards.map((card) => (
                <article key={card.label} className="analytics-card">
                  <span className="analytics-card-label">{card.label}</span>
                  <strong className="analytics-card-value">{card.value}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="analytics-charts">
            {aiClassificationChart.length > 0 && (
              <AnalyticsChart
                title="Accepted AI Classification vs Manually Overridden Classification"
                data={aiClassificationChart}
              />
            )}
            {chartSections.map((section) => (
              <AnalyticsChart key={section.title} title={section.title} data={section.data} />
            ))}
          </section>
        </>
      )}
    </div>
  );
}

export default Analytics;
