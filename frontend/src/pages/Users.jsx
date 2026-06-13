import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getUsers } from '../api/api.js';
import './Users.css';

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

  return 'Failed to load users.';
}

function getDisplayName(user) {
  return user.full_name || user.name || '—';
}

function Users() {
  const isAdmin = localStorage.getItem('role') === 'ADMIN';
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(isAdmin);
  const [error, setError] = useState('');

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getUsers();
      setUsers(response.data);
    } catch (err) {
      setUsers([]);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchUsers();
    }
  }, [fetchUsers, isAdmin]);

  if (!isAdmin) {
    return (
      <div className="users-page">
        <div className="users-access-denied">
          <h1>Access Denied</h1>
          <p>User management is available to administrators only.</p>
          <Link to="/tickets" className="users-link-button">
            Go to Tickets
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="users-page">
      <div className="users-header">
        <div>
          <h1>Users</h1>
          <p className="users-subtitle">View registered internal dashboard users</p>
        </div>
        <button type="button" className="users-refresh" onClick={fetchUsers} disabled={loading}>
          Refresh
        </button>
      </div>

      {loading && <p className="users-message">Loading users...</p>}
      {!loading && error && <p className="users-error">{error}</p>}
      {!loading && !error && users.length === 0 && (
        <p className="users-message">No users found.</p>
      )}

      {!loading && !error && users.length > 0 && (
        <div className="users-table-wrapper">
          <table className="users-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="users-name">{getDisplayName(user)}</td>
                  <td>{user.email}</td>
                  <td>
                    <span className={`users-role-badge users-role-${user.role?.toLowerCase()}`}>
                      {user.role}
                    </span>
                  </td>
                  <td>{formatDate(user.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Users;
