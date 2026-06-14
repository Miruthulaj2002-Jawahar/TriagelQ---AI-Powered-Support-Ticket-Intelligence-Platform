import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCurrentUser, getTickets, changePassword } from '../api/api.js';
import { PriorityBadge, SentimentBadge, StatusBadge } from '../utils/badges.jsx';
import './Profile.css';

function formatDate(value) {
  if (!value) return '—';
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

function getDisplayName(user) {
  return user?.full_name || user?.name || '—';
}

function countTicketsByStatus(tickets, status) {
  return tickets.filter((ticket) => ticket.status === status).length;
}

function buildTicketCounts(tickets) {
  return {
    total: tickets.length,
    open: countTicketsByStatus(tickets, 'OPEN'),
    inProgress: countTicketsByStatus(tickets, 'IN_PROGRESS'),
    resolved: countTicketsByStatus(tickets, 'RESOLVED'),
    closed: countTicketsByStatus(tickets, 'CLOSED'),
  };
}

function Profile() {
  const [user, setUser] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordValidationError, setPasswordValidationError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  const fetchProfileData = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [userResponse, ticketsResponse] = await Promise.all([
        getCurrentUser(),
        getTickets(),
      ]);

      setUser(userResponse.data);
      setTickets(ticketsResponse.data);
    } catch (err) {
      setUser(null);
      setTickets([]);
      setError(getErrorMessage(err, 'Failed to load profile data.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfileData();
  }, [fetchProfileData]);

  const isAdmin = user?.role === 'ADMIN';
  const ticketCounts = useMemo(() => buildTicketCounts(tickets), [tickets]);

  const recentTickets = useMemo(
    () =>
      [...tickets]
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5),
    [tickets],
  );

  const adminCards = [
    { label: 'Total Tickets', value: ticketCounts.total },
    { label: 'Open Tickets', value: ticketCounts.open },
    { label: 'In Progress Tickets', value: ticketCounts.inProgress },
    { label: 'Resolved Tickets', value: ticketCounts.resolved },
    { label: 'Closed Tickets', value: ticketCounts.closed },
  ];

  const agentCards = [
    { label: 'Assigned Tickets', value: ticketCounts.total },
    { label: 'Open Tickets', value: ticketCounts.open },
    { label: 'In Progress Tickets', value: ticketCounts.inProgress },
    { label: 'Resolved Tickets', value: ticketCounts.resolved },
    { label: 'Closed Tickets', value: ticketCounts.closed },
  ];

  const overviewCards = isAdmin ? adminCards : agentCards;
  const overviewTitle = isAdmin ? 'Admin Work Overview' : 'My Ticket Progress';
  const tableTitle = isAdmin ? 'Recent Tickets' : 'My Tickets';
  const tableTickets = isAdmin ? recentTickets : tickets;

  const handlePasswordChange = (event) => {
    const { name, value } = event.target;
    setPasswordForm((prev) => ({ ...prev, [name]: value }));
  };

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setPasswordValidationError('');
    setPasswordSuccess('');
    setPasswordError('');

    const { currentPassword, newPassword, confirmPassword } = passwordForm;

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordValidationError('All password fields are required.');
      return;
    }

    if (newPassword.length < 6) {
      setPasswordValidationError('New password must be at least 6 characters.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordValidationError('New password and confirm password must match.');
      return;
    }

    setChangingPassword(true);

    try {
      await changePassword(currentPassword, newPassword);
      setPasswordSuccess('Password changed successfully.');
      setPasswordForm({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
    } catch (err) {
      setPasswordError(getErrorMessage(err, 'Failed to change password.'));
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="profile-page">
      <div className="profile-header">
        <div>
          <h1>Profile</h1>
          <p className="profile-subtitle">Your account and ticket overview</p>
        </div>
        <button type="button" className="profile-refresh" onClick={fetchProfileData} disabled={loading}>
          Refresh
        </button>
      </div>

      {loading && <p className="profile-message">Loading profile...</p>}
      {!loading && error && <p className="profile-error">{error}</p>}

      {!loading && !error && user && (
        <>
          <section className="profile-section">
            <h2>Account Information</h2>
            <dl className="profile-details">
              <div className="profile-row">
                <dt>Name</dt>
                <dd>{getDisplayName(user)}</dd>
              </div>
              <div className="profile-row">
                <dt>Email</dt>
                <dd>{user.email}</dd>
              </div>
              <div className="profile-row">
                <dt>Role</dt>
                <dd>
                  <span className={`profile-role-badge profile-role-${user.role?.toLowerCase()}`}>
                    {user.role}
                  </span>
                </dd>
              </div>
              {user.created_at && (
                <div className="profile-row">
                  <dt>Created At</dt>
                  <dd>{formatDate(user.created_at)}</dd>
                </div>
              )}
            </dl>
          </section>

          <section className="profile-section">
            <h2>Change Password</h2>
            <form className="profile-password-form" onSubmit={handlePasswordSubmit}>
              <label htmlFor="currentPassword">Current Password</label>
              <input
                id="currentPassword"
                name="currentPassword"
                type="password"
                value={passwordForm.currentPassword}
                onChange={handlePasswordChange}
                autoComplete="current-password"
              />

              <label htmlFor="newPassword">New Password</label>
              <input
                id="newPassword"
                name="newPassword"
                type="password"
                value={passwordForm.newPassword}
                onChange={handlePasswordChange}
                autoComplete="new-password"
              />

              <label htmlFor="confirmPassword">Confirm New Password</label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={passwordForm.confirmPassword}
                onChange={handlePasswordChange}
                autoComplete="new-password"
              />

              {passwordValidationError && (
                <p className="profile-error">{passwordValidationError}</p>
              )}
              {passwordError && <p className="profile-error">{passwordError}</p>}
              {passwordSuccess && <p className="profile-success">{passwordSuccess}</p>}

              <button type="submit" className="profile-password-button" disabled={changingPassword}>
                {changingPassword ? 'Changing Password...' : 'Change Password'}
              </button>
            </form>
          </section>

          <section className="profile-section">
            <h2>{overviewTitle}</h2>
            <div className="profile-cards">
              {overviewCards.map((card) => (
                <article key={card.label} className="profile-card">
                  <span className="profile-card-label">{card.label}</span>
                  <strong className="profile-card-value">{card.value}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="profile-section">
            <h2>{tableTitle}</h2>
            {tableTickets.length === 0 ? (
              <p className="profile-message">
                {isAdmin ? 'No tickets found.' : 'No assigned tickets found.'}
              </p>
            ) : (
              <div className="profile-table-wrapper">
                <table className="profile-table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Customer Email</th>
                      <th>Status</th>
                      <th>Priority</th>
                      <th>Sentiment</th>
                      <th>Created At</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableTickets.map((ticket) => (
                      <tr key={ticket.id}>
                        <td className="profile-ticket-title">{ticket.title}</td>
                        <td>{ticket.customer_email}</td>
                        <td>
                          <StatusBadge value={ticket.status} />
                        </td>
                        <td>
                          <PriorityBadge value={ticket.priority} />
                        </td>
                        <td>
                          <SentimentBadge value={ticket.sentiment} />
                        </td>
                        <td>{formatDate(ticket.created_at)}</td>
                        <td>
                          <Link to={`/tickets/${ticket.id}`} className="profile-view-link">
                            View Details
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default Profile;
