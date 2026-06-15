import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  getAgents,
  getTicketById,
  overrideTicket,
  resetTicketOverride,
  updateTicket,
} from '../api/api.js';
import { useUserRole } from '../hooks/useUserRole.js';
import { formatAgentOptionLabel, getAssignedAgentLabel } from '../utils/assignmentHelpers.js';
import { PriorityBadge } from '../utils/badges.jsx';
import { renderDetailValue } from '../utils/renderDetailValue.jsx';
import './TicketDetail.css';

const STATUS_OPTIONS = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];
const PRIORITY_OPTIONS = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];
const CATEGORY_OPTIONS = [
  'Billing',
  'Technical',
  'Account',
  'Feature Request',
  'Complaint',
  'General',
];

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

function getEffectiveFormValues(ticket) {
  return {
    category: ticket?.category || ticket?.ai_category || '',
    priority: ticket?.priority || ticket?.ai_priority || '',
    reason: ticket?.override_reason || '',
  };
}

function getOverriddenByLabel(ticket) {
  if (ticket?.overridden_by_name && ticket?.overridden_by_email) {
    return `${ticket.overridden_by_name} (${ticket.overridden_by_email})`;
  }
  if (ticket?.overridden_by_name) {
    return ticket.overridden_by_name;
  }
  if (ticket?.overridden_by_email) {
    return ticket.overridden_by_email;
  }
  return ticket?.overridden_by || null;
}

function buildEffectiveFields(ticket) {
  if (!ticket) return [];

  return [
    { label: 'Effective Category', value: ticket.category },
    { label: 'Effective Priority', value: ticket.priority, badge: 'priority' },
  ].filter((field) => field.value !== null && field.value !== undefined && field.value !== '');
}

function buildAiFields(ticket) {
  if (!ticket) return [];

  return [
    { label: 'AI Category', value: ticket.ai_category },
    { label: 'AI Priority', value: ticket.ai_priority, badge: 'priority' },
    { label: 'AI Sentiment', value: ticket.ai_sentiment, badge: 'sentiment' },
    { label: 'AI Confidence', value: ticket.ai_confidence },
    { label: 'AI Explanation', value: ticket.ai_explanation },
  ].filter((field) => field.value !== null && field.value !== undefined && field.value !== '');
}

function buildOverrideFields(ticket) {
  if (!ticket?.has_manual_override) return [];

  const overriddenBy = getOverriddenByLabel(ticket);

  return [
    { label: 'Category Override', value: ticket.category_override },
    { label: 'Priority Override', value: ticket.priority_override, badge: 'priority' },
    { label: 'Override Reason', value: ticket.override_reason },
    { label: 'Overridden By', value: overriddenBy },
    { label: 'Overridden At', value: formatDate(ticket.overridden_at) },
  ].filter((field) => field.value !== null && field.value !== undefined && field.value !== '');
}

function buildDetailFields(ticket) {
  if (!ticket) return [];

  return [
    { label: 'ID', value: ticket.id },
    { label: 'Title', value: ticket.title },
    { label: 'Description', value: ticket.description },
    { label: 'Customer Email', value: ticket.customer_email },
    { label: 'Status', value: ticket.status, badge: 'status' },
    { label: 'Sentiment', value: ticket.sentiment, badge: 'sentiment' },
    { label: 'Assigned Queue', value: ticket.assigned_queue },
    { label: 'Assigned Agent', value: getAssignedAgentLabel(ticket) },
    { label: 'Created At', value: formatDate(ticket.created_at) },
    { label: 'Updated At', value: formatDate(ticket.updated_at) },
  ].filter((field) => field.value !== null && field.value !== undefined && field.value !== '');
}

function TicketDetail() {
  const { id } = useParams();
  const { isAdmin, loading: roleLoading } = useUserRole();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusError, setStatusError] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [agents, setAgents] = useState([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [agentsError, setAgentsError] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [assignmentMessage, setAssignmentMessage] = useState('');
  const [assignmentError, setAssignmentError] = useState('');
  const [updatingAssignment, setUpdatingAssignment] = useState(false);
  const [overrideCategory, setOverrideCategory] = useState('');
  const [overridePriority, setOverridePriority] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideMessage, setOverrideMessage] = useState('');
  const [overrideError, setOverrideError] = useState('');
  const [submittingOverride, setSubmittingOverride] = useState(false);
  const [resettingOverride, setResettingOverride] = useState(false);

  const applyTicketToForm = useCallback((ticketData) => {
    const formValues = getEffectiveFormValues(ticketData);
    setOverrideCategory(formValues.category);
    setOverridePriority(formValues.priority);
    setOverrideReason(formValues.reason);
    setSelectedAgentId(ticketData?.assigned_agent_id || '');
  }, []);

  const fetchAgents = useCallback(async () => {
    if (!isAdmin) {
      return;
    }

    setAgentsLoading(true);
    setAgentsError('');

    try {
      const response = await getAgents();
      setAgents(response.data);
    } catch (err) {
      setAgents([]);
      setAgentsError(getErrorMessage(err, 'Failed to load agents.'));
    } finally {
      setAgentsLoading(false);
    }
  }, [isAdmin]);

  const fetchTicket = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getTicketById(id);
      setTicket(response.data);
      setSelectedStatus(response.data.status || 'OPEN');
      applyTicketToForm(response.data);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load ticket details.'));
      setTicket(null);
    } finally {
      setLoading(false);
    }
  }, [applyTicketToForm, id]);

  useEffect(() => {
    const frameId = requestAnimationFrame(() => {
      fetchTicket();
      if (!roleLoading && isAdmin) {
        fetchAgents();
      }
    });
    return () => cancelAnimationFrame(frameId);
  }, [fetchTicket, fetchAgents, isAdmin, roleLoading]);

  const handleAssignmentUpdate = async (event) => {
    event.preventDefault();
    setAssignmentMessage('');
    setAssignmentError('');
    setUpdatingAssignment(true);

    try {
      const payload = {
        assigned_agent_id: selectedAgentId || null,
      };
      const response = await updateTicket(id, payload);
      setTicket(response.data);
      applyTicketToForm(response.data);
      setAssignmentMessage('Ticket assignment updated successfully.');
    } catch (err) {
      setAssignmentError(getErrorMessage(err, 'Failed to update assignment.'));
    } finally {
      setUpdatingAssignment(false);
    }
  };

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

  const handleOverrideSubmit = async (event) => {
    event.preventDefault();
    setOverrideMessage('');
    setOverrideError('');

    if (!overrideCategory || !overridePriority) {
      setOverrideError('Category and priority are required.');
      return;
    }

    setSubmittingOverride(true);

    try {
      const payload = {
        category: overrideCategory,
        priority: overridePriority,
      };
      if (overrideReason.trim()) {
        payload.override_reason = overrideReason.trim();
      }

      const response = await overrideTicket(id, payload);
      setTicket(response.data);
      applyTicketToForm(response.data);
      setOverrideMessage('Manual override applied successfully.');
    } catch (err) {
      setOverrideError(getErrorMessage(err, 'Failed to apply manual override.'));
    } finally {
      setSubmittingOverride(false);
    }
  };

  const handleResetOverride = async () => {
    setOverrideMessage('');
    setOverrideError('');

    const confirmed = window.confirm('Reset this ticket to the original AI classification?');
    if (!confirmed) {
      return;
    }

    setResettingOverride(true);

    try {
      const response = await resetTicketOverride(id);
      setTicket(response.data);
      applyTicketToForm(response.data);
      setOverrideMessage('Ticket reset to AI classification.');
    } catch (err) {
      setOverrideError(getErrorMessage(err, 'Failed to reset override.'));
    } finally {
      setResettingOverride(false);
    }
  };

  const detailFields = buildDetailFields(ticket);
  const aiFields = buildAiFields(ticket);
  const effectiveFields = buildEffectiveFields(ticket);
  const overrideFields = buildOverrideFields(ticket);

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
            <h2>Original AI Classification</h2>
            <p className="panel-note">These values are preserved even after manual overrides.</p>
            <dl className="ticket-detail-fields">
              {aiFields.map((field) => (
                <div key={field.label} className="detail-row">
                  <dt>{field.label}</dt>
                  <dd>{renderDetailValue(field)}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="ticket-detail-panel">
            <h2>Current Effective Classification</h2>
            <dl className="ticket-detail-fields">
              {effectiveFields.map((field) => (
                <div key={field.label} className="detail-row">
                  <dt>{field.label}</dt>
                  <dd>{renderDetailValue(field)}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="ticket-detail-panel">
            <h2>Manual Override Details</h2>
            {ticket.has_manual_override ? (
              <dl className="ticket-detail-fields">
                {overrideFields.map((field) => (
                  <div key={field.label} className="detail-row">
                    <dt>{field.label}</dt>
                    <dd>
                      {field.badge === 'priority' ? (
                        <PriorityBadge value={field.value} />
                      ) : (
                        field.value
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="panel-note">No manual override has been applied.</p>
            )}
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
              <h2>Assign to Agent</h2>
              <p className="panel-note">
                Assigned Agent: {getAssignedAgentLabel(ticket)}
              </p>
              <p className="panel-note">
                Select an agent below to assign or reassign this ticket. Choose Unassigned to
                remove ownership.
              </p>

              <form className="ticket-update-form" onSubmit={handleAssignmentUpdate}>
                <label htmlFor="assigned-agent">Assign to Agent</label>
                <select
                  id="assigned-agent"
                  value={selectedAgentId}
                  onChange={(event) => setSelectedAgentId(event.target.value)}
                  disabled={agentsLoading}
                >
                  <option value="">Unassigned</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {formatAgentOptionLabel(agent)}
                    </option>
                  ))}
                </select>

                {agentsLoading && <p className="ticket-detail-message">Loading agents...</p>}
                {agentsError && <p className="ticket-detail-error">{agentsError}</p>}

                <button
                  type="submit"
                  className="btn-primary"
                  disabled={updatingAssignment || agentsLoading}
                >
                  {updatingAssignment ? 'Saving Assignment...' : 'Save Assignment'}
                </button>
              </form>
              {assignmentMessage && <p className="ticket-detail-success">{assignmentMessage}</p>}
              {assignmentError && <p className="ticket-detail-error">{assignmentError}</p>}
            </section>
          )}

          <section className="ticket-detail-panel">
            <h2>Manual Override</h2>
            <p className="panel-note">
              Correct the AI category and/or priority. Original AI values remain stored separately.
            </p>

            <form className="ticket-update-form" onSubmit={handleOverrideSubmit}>
              <label htmlFor="override-category">Category</label>
              <select
                id="override-category"
                value={overrideCategory}
                onChange={(event) => setOverrideCategory(event.target.value)}
                required
              >
                {CATEGORY_OPTIONS.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>

              <label htmlFor="override-priority">Priority</label>
              <select
                id="override-priority"
                value={overridePriority}
                onChange={(event) => setOverridePriority(event.target.value)}
                required
              >
                {PRIORITY_OPTIONS.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </select>

              <label htmlFor="override-reason">Reason (optional)</label>
              <input
                id="override-reason"
                type="text"
                value={overrideReason}
                onChange={(event) => setOverrideReason(event.target.value)}
                placeholder="Why is this override needed?"
              />

              <div className="ticket-detail-actions">
                <button type="submit" className="btn-secondary" disabled={submittingOverride}>
                  {submittingOverride ? 'Applying Override...' : 'Apply Override'}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleResetOverride}
                  disabled={resettingOverride || !ticket.has_manual_override}
                >
                  {resettingOverride ? 'Resetting...' : 'Reset to AI Classification'}
                </button>
              </div>
            </form>
            {overrideMessage && <p className="ticket-detail-success">{overrideMessage}</p>}
            {overrideError && <p className="ticket-detail-error">{overrideError}</p>}
          </section>
        </>
      )}
    </div>
  );
}

export default TicketDetail;
