import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getTicketById, updateTicket } from '../api/api.js';
import { renderDetailValue } from '../utils/badges.jsx';
import './TicketDetail.css';

const STATUS_OPTIONS = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];
const PRIORITY_OPTIONS = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];
const SENTIMENT_OPTIONS = ['POSITIVE', 'NEUTRAL', 'NEGATIVE'];

function formatDate(value) {
  if (!value) return null;
  return new Date(value).toLocaleString();
}

function getErrorMessage(error, fallback) {
  const detail = error.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ');
  }

  return fallback;
}

function getConfidence(ticket) {
  return ticket?.confidence ?? ticket?.classification_confidence;
}

function getExplanation(ticket) {
  return ticket?.explanation ?? ticket?.classification_explanation;
}

function buildDetailFields(ticket) {
  if (!ticket) return [];

  return [
    { label: 'ID', value: ticket.id },
    { label: 'Title', value: ticket.title },
    { label: 'Description', value: ticket.description },
    { label: 'Customer Email', value: ticket.customer_email },
    { label: 'Status', value: ticket.status, badge: 'status' },
    { label: 'Category', value: ticket.category },
    { label: 'Priority', value: ticket.priority, badge: 'priority' },
    { label: 'Sentiment', value: ticket.sentiment, badge: 'sentiment' },
    { label: 'Confidence', value: getConfidence(ticket) },
    { label: 'Explanation', value: getExplanation(ticket) },
    { label: 'Assigned Queue', value: ticket.assigned_queue },
    { label: 'Created At', value: formatDate(ticket.created_at) },
    { label: 'Updated At', value: formatDate(ticket.updated_at) },
  ].filter((field) => field.value !== null && field.value !== undefined && field.value !== '');
}

function TicketDetail() {
  const { id } = useParams();
  const isAdmin = localStorage.getItem('role') === 'ADMIN';
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusError, setStatusError] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [overrideCategory, setOverrideCategory] = useState('');
  const [overridePriority, setOverridePriority] = useState('');
  const [overrideSentiment, setOverrideSentiment] = useState('');
  const [overrideMessage, setOverrideMessage] = useState('');
  const [overrideError, setOverrideError] = useState('');
  const [updatingOverrides, setUpdatingOverrides] = useState(false);

  const fetchTicket = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getTicketById(id);
      setTicket(response.data);
      setSelectedStatus(response.data.status || 'OPEN');
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load ticket details.'));
      setTicket(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTicket();
  }, [fetchTicket]);

  const handleStatusUpdate = async (event) => {
    event.preventDefault();
    setStatusMessage('');
    setStatusError('');
    setUpdatingStatus(true);

    try {
      const response = await updateTicket(id, { status: selectedStatus });
      setTicket(response.data);
      setSelectedStatus(response.data.status);
      setStatusMessage('Status updated successfully.');
    } catch (err) {
      setStatusError(getErrorMessage(err, 'Failed to update status.'));
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleOverrideUpdate = async (event) => {
    event.preventDefault();
    setOverrideMessage('');
    setOverrideError('');

    const payload = {};
    if (overrideCategory.trim()) payload.category = overrideCategory.trim();
    if (overridePriority) payload.priority = overridePriority;
    if (overrideSentiment) payload.sentiment = overrideSentiment;

    if (Object.keys(payload).length === 0) {
      setOverrideError('Enter at least one override value before applying.');
      return;
    }

    setUpdatingOverrides(true);

    try {
      const response = await updateTicket(id, payload);
      setTicket(response.data);
      setSelectedStatus(response.data.status || selectedStatus);
      setOverrideMessage('Overrides applied successfully.');
      setOverrideCategory('');
      setOverridePriority('');
      setOverrideSentiment('');
    } catch (err) {
      setOverrideError(getErrorMessage(err, 'Failed to apply overrides.'));
    } finally {
      setUpdatingOverrides(false);
    }
  };

  const detailFields = buildDetailFields(ticket);

  return (
    <div className="ticket-detail-page">
      <div className="ticket-detail-header">
        <Link to="/tickets" className="back-link">
          ← Back to Tickets
        </Link>
        <h1>Ticket Details</h1>
      </div>

      {loading && <p className="ticket-detail-message">Loading ticket...</p>}
      {!loading && error && <p className="ticket-detail-error">{error}</p>}

      {!loading && !error && ticket && (
        <>
          <section className="ticket-detail-panel">
            <h2>{ticket.title}</h2>
            <dl className="ticket-detail-fields">
              {detailFields.map((field) => (
                <div key={field.label} className="detail-row">
                  <dt>{field.label}</dt>
                  <dd>{renderDetailValue(field)}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="ticket-detail-panel">
            <h2>Update Status</h2>
            <form className="ticket-update-form" onSubmit={handleStatusUpdate}>
              <label htmlFor="status">Status</label>
              <select
                id="status"
                value={selectedStatus}
                onChange={(event) => setSelectedStatus(event.target.value)}
              >
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {status.replace('_', ' ')}
                  </option>
                ))}
              </select>

              <button type="submit" className="btn-primary" disabled={updatingStatus}>
                {updatingStatus ? 'Updating...' : 'Update Status'}
              </button>
            </form>
            {statusMessage && <p className="ticket-detail-success">{statusMessage}</p>}
            {statusError && <p className="ticket-detail-error">{statusError}</p>}
          </section>

          {isAdmin && (
          <section className="ticket-detail-panel">
            <h2>Manual Overrides</h2>
            <p className="panel-note">Optional. Only filled fields are sent to the backend.</p>

            <form className="ticket-update-form" onSubmit={handleOverrideUpdate}>
              <label htmlFor="override-category">Override Category</label>
              <input
                id="override-category"
                type="text"
                value={overrideCategory}
                onChange={(event) => setOverrideCategory(event.target.value)}
                placeholder="e.g. Billing"
              />

              <label htmlFor="override-priority">Override Priority</label>
              <select
                id="override-priority"
                value={overridePriority}
                onChange={(event) => setOverridePriority(event.target.value)}
              >
                <option value="">Select priority</option>
                {PRIORITY_OPTIONS.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </select>

              <label htmlFor="override-sentiment">Override Sentiment</label>
              <select
                id="override-sentiment"
                value={overrideSentiment}
                onChange={(event) => setOverrideSentiment(event.target.value)}
              >
                <option value="">Select sentiment</option>
                {SENTIMENT_OPTIONS.map((sentiment) => (
                  <option key={sentiment} value={sentiment}>
                    {sentiment}
                  </option>
                ))}
              </select>

              <button type="submit" className="btn-secondary" disabled={updatingOverrides}>
                {updatingOverrides ? 'Applying...' : 'Apply Overrides'}
              </button>
            </form>
            {overrideMessage && <p className="ticket-detail-success">{overrideMessage}</p>}
            {overrideError && <p className="ticket-detail-error">{overrideError}</p>}
          </section>
          )}
        </>
      )}
    </div>
  );
}

export default TicketDetail;
