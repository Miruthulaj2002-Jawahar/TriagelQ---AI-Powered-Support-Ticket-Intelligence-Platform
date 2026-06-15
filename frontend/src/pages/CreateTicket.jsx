import { useState } from 'react';
import { Link } from 'react-router-dom';
import { createTicket } from '../api/api.js';
import { renderDetailValue } from '../utils/renderDetailValue.jsx';
import './CreateTicket.css';

const EMPTY_FORM = {
  title: '',
  description: '',
  customer_email: '',
};

function formatDate(value) {
  if (!value) return null;
  return new Date(value).toLocaleString();
}

function getErrorMessage(error) {
  const detail = error.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ');
  }

  return 'Failed to create ticket. Please try again.';
}

function getConfidence(ticket) {
  return ticket.confidence ?? ticket.classification_confidence;
}

function getExplanation(ticket) {
  return ticket.explanation ?? ticket.classification_explanation;
}

function CreateTicket() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [validationError, setValidationError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [createdTicket, setCreatedTicket] = useState(null);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setValidationError('');
    setSubmitError('');

    const title = form.title.trim();
    const description = form.description.trim();
    const customer_email = form.customer_email.trim();

    if (!title || !description || !customer_email) {
      setValidationError('Please fill in all fields before submitting.');
      return;
    }

    setSubmitting(true);

    try {
      const response = await createTicket({
        title,
        description,
        customer_email,
      });
      setCreatedTicket(response.data);
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateAnother = () => {
    setForm(EMPTY_FORM);
    setCreatedTicket(null);
    setValidationError('');
    setSubmitError('');
  };

  const confidence = createdTicket ? getConfidence(createdTicket) : null;
  const explanation = createdTicket ? getExplanation(createdTicket) : null;

  const detailFields = createdTicket
    ? [
        { label: 'ID', value: createdTicket.id },
        { label: 'Title', value: createdTicket.title },
        { label: 'Description', value: createdTicket.description },
        { label: 'Customer Email', value: createdTicket.customer_email },
        { label: 'Status', value: createdTicket.status, badge: 'status' },
        { label: 'Category', value: createdTicket.category },
        { label: 'Priority', value: createdTicket.priority, badge: 'priority' },
        { label: 'Sentiment', value: createdTicket.sentiment, badge: 'sentiment' },
        { label: 'Confidence', value: confidence },
        { label: 'Explanation', value: explanation },
        { label: 'Assigned Queue', value: createdTicket.assigned_queue },
        { label: 'Created At', value: formatDate(createdTicket.created_at) },
      ].filter((field) => field.value !== null && field.value !== undefined && field.value !== '')
    : [];

  return (
    <div className="create-ticket-page">
      <div className="create-ticket-header">
        <h1>Create Ticket</h1>
        <p className="create-ticket-subtitle">
          Submit a new support ticket. AI classification runs automatically on the backend.
        </p>
      </div>

      {!createdTicket && (
        <form className="create-ticket-form" onSubmit={handleSubmit}>
          <label htmlFor="title">Title</label>
          <input
            id="title"
            name="title"
            type="text"
            value={form.title}
            onChange={handleChange}
            placeholder="Brief summary of the issue"
          />

          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={form.description}
            onChange={handleChange}
            rows={6}
            placeholder="Describe the issue in detail"
          />

          <label htmlFor="customer_email">Customer Email</label>
          <input
            id="customer_email"
            name="customer_email"
            type="email"
            value={form.customer_email}
            onChange={handleChange}
            placeholder="customer@example.com"
          />

          {validationError && <p className="create-ticket-error">{validationError}</p>}
          {submitError && <p className="create-ticket-error">{submitError}</p>}

          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? 'Creating ticket...' : 'Create Ticket'}
          </button>
        </form>
      )}

      {createdTicket && (
        <div className="create-ticket-success">
          <p className="success-message">Ticket created successfully.</p>

          <div className="classification-panel">
            <h2>AI Classification Result</h2>
            <p className="classification-note">
              Category, priority, sentiment, and queue were assigned automatically.
            </p>

            <dl className="ticket-details">
              {detailFields.map((field) => (
                <div key={field.label} className="detail-row">
                  <dt>{field.label}</dt>
                  <dd>{renderDetailValue(field)}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="create-ticket-actions">
            <button type="button" className="btn-secondary" onClick={handleCreateAnother}>
              Create Another Ticket
            </button>
            <Link to="/tickets" className="btn-primary">
              View Tickets
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default CreateTicket;
