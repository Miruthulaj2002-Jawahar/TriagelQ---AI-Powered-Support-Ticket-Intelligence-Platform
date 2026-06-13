import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getTickets } from '../api/api.js';
import './Tickets.css';

const STATUS_OPTIONS = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];
const PRIORITY_OPTIONS = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];

function formatDate(value) {
  if (!value) return '—';
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

  return 'Failed to load tickets. Please try again.';
}

function Tickets() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getTickets();
      setTickets(response.data);
    } catch (err) {
      setError(getErrorMessage(err));
      setTickets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const categoryOptions = useMemo(() => {
    const categories = tickets
      .map((ticket) => ticket.category)
      .filter(Boolean);

    return [...new Set(categories)].sort();
  }, [tickets]);

  const filteredTickets = useMemo(() => {
    const query = search.trim().toLowerCase();

    return tickets.filter((ticket) => {
      const matchesSearch =
        !query ||
        ticket.title?.toLowerCase().includes(query) ||
        ticket.customer_email?.toLowerCase().includes(query);

      const matchesStatus = !statusFilter || ticket.status === statusFilter;
      const matchesCategory = !categoryFilter || ticket.category === categoryFilter;
      const matchesPriority = !priorityFilter || ticket.priority === priorityFilter;

      return matchesSearch && matchesStatus && matchesCategory && matchesPriority;
    });
  }, [tickets, search, statusFilter, categoryFilter, priorityFilter]);

  return (
    <div className="tickets-page">
      <div className="tickets-header">
        <div>
          <h1>Tickets</h1>
          <p className="tickets-subtitle">View and manage support tickets</p>
        </div>

        <div className="tickets-header-actions">
          <button type="button" className="btn-secondary" onClick={fetchTickets} disabled={loading}>
            Refresh
          </button>
          <Link to="/create-ticket" className="btn-primary">
            Create Ticket
          </Link>
        </div>
      </div>

      <div className="tickets-filters">
        <input
          type="text"
          placeholder="Search by title or customer email..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {status.replace('_', ' ')}
            </option>
          ))}
        </select>

        <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
          <option value="">All categories</option>
          {categoryOptions.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>

        <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
          <option value="">All priorities</option>
          {PRIORITY_OPTIONS.map((priority) => (
            <option key={priority} value={priority}>
              {priority}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="tickets-message">Loading tickets...</p>}
      {!loading && error && <p className="tickets-error">{error}</p>}
      {!loading && !error && tickets.length === 0 && (
        <p className="tickets-message">No tickets found.</p>
      )}
      {!loading && !error && tickets.length > 0 && filteredTickets.length === 0 && (
        <p className="tickets-message">No tickets match your filters.</p>
      )}

      {!loading && !error && filteredTickets.length > 0 && (
        <div className="tickets-table-wrapper">
          <table className="tickets-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Customer Email</th>
                <th>Status</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Sentiment</th>
                <th>Assigned Queue</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {filteredTickets.map((ticket) => (
                <tr key={ticket.id}>
                  <td className="ticket-title">{ticket.title}</td>
                  <td>{ticket.customer_email}</td>
                  <td>
                    <span className={`badge badge-status badge-${ticket.status?.toLowerCase()}`}>
                      {ticket.status?.replace('_', ' ')}
                    </span>
                  </td>
                  <td>{ticket.category || '—'}</td>
                  <td>
                    <span className={`badge badge-priority badge-${ticket.priority?.toLowerCase()}`}>
                      {ticket.priority}
                    </span>
                  </td>
                  <td>
                    <span className={`badge badge-sentiment badge-${ticket.sentiment?.toLowerCase()}`}>
                      {ticket.sentiment}
                    </span>
                  </td>
                  <td>{ticket.assigned_queue || '—'}</td>
                  <td>{formatDate(ticket.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Tickets;
