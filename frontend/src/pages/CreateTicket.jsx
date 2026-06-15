import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createTicket, getAgents } from '../api/api.js';
import { useUserRole } from '../hooks/useUserRole.js';
import { formatAgentOptionLabel, getAssignedAgentLabel } from '../utils/assignmentHelpers.js';
import { renderDetailValue } from '../utils/renderDetailValue.jsx';
import './CreateTicket.css';

const EMPTY_FORM = {
  title: '',
  description: '',
  customer_email: '',
  assigned_agent_id: '',
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
  const { isAdmin, loading: roleLoading } = useUserRole();
  const [form, setForm] = useState(EMPTY_FORM);
  const [agents, setAgents] = useState([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [agentsError, setAgentsError] = useState('');
  const [validationError, setValidationError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [createdTicket, setCreatedTicket] = useState(null);

  const fetchAgents = useCallback(async () => {
    if (!isAdmin) {
      return;
    }

    setAgentsLoading(true);
    setAgentsError('');

    try {
      const response = await getAgents();
      setAgents(response.data);
    } catch (error) {
      setAgents([]);
      setAgentsError(getErrorMessage(error));
    } finally {
      setAgentsLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    if (roleLoading || !isAdmin) {
      return undefined;
    }

    const frameId = requestAnimationFrame(() => {
      fetchAgents();
    });
    return () => cancelAnimationFrame(frameId);
  }, [fetchAgents, isAdmin, roleLoading]);

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
      setValidationError('Please fill in all required fields before submitting.');
      return;
    }

    setSubmitting(true);

    try {
      const payload = {
        title,
        description,
        customer_email,
      };

      if (isAdmin && form.assigned_agent_id) {
        payload.assigned_agent_id = form.assigned_agent_id;
      }

      const response = await createTicket(payload);
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
        { label: 'Assigned Agent', value: getAssignedAgentLabel(createdTicket) },
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

          {isAdmin && (
            <>
              <label htmlFor="assigned_agent_id">Assign to Agent</label>
              <select
                id="assigned_agent_id"
                name="assigned_agent_id"
                value={form.assigned_agent_id}
                onChange={handleChange}
                disabled={agentsLoading}
              >
                <option value="">Unassigned</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {formatAgentOptionLabel(agent)}
                  </option>
                ))}
              </select>
              {agentsLoading && <p className="create-ticket-message">Loading agents...</p>}
              {agentsError && <p className="create-ticket-error">{agentsError}</p>}
            </>
          )}

          {validationError && <p className="create-ticket-error">{validationError}</p>}
          {submitError && <p className="create-ticket-error">{submitError}</p>}

          <button type="submit" className="btn-primary" disabled={submitting || agentsLoading}>
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
