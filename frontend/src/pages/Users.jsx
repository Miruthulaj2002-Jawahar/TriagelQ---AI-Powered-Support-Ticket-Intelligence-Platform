import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createUser, deactivateUser, getCurrentUser, getUsers } from '../api/api.js';
import './Users.css';

const EMPTY_FORM = {
  name: '',
  email: '',
  password: '',
  role: 'AGENT',
};

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function getErrorMessage(error, fallback = 'Failed to load users.') {
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
  return user.full_name || user.name || '—';
}

function Users() {
  const isAdmin = localStorage.getItem('role') === 'ADMIN';
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(isAdmin);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');
  const [creating, setCreating] = useState(false);
  const [currentUserId, setCurrentUserId] = useState('');
  const [deactivateError, setDeactivateError] = useState('');
  const [deactivateSuccess, setDeactivateSuccess] = useState('');
  const [deactivatingUserId, setDeactivatingUserId] = useState('');

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
    if (!isAdmin) {
      return undefined;
    }
    const frameId = requestAnimationFrame(() => {
      fetchUsers();
      getCurrentUser()
        .then((response) => setCurrentUserId(response.data.id))
        .catch(() => setCurrentUserId(''));
    });
    return () => cancelAnimationFrame(frameId);
  }, [fetchUsers, isAdmin]);

  const handleFormChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateUser = async (event) => {
    event.preventDefault();
    setCreateError('');
    setCreateSuccess('');

    const name = form.name.trim();
    const email = form.email.trim();
    const password = form.password;

    if (!name || !email || !password || !form.role) {
      setCreateError('All fields are required.');
      return;
    }

    if (password.length < 8) {
      setCreateError('Password must be at least 8 characters.');
      return;
    }

    setCreating(true);

    try {
      await createUser({
        name,
        email,
        password,
        role: form.role,
      });
      setCreateSuccess('User created successfully.');
      setForm(EMPTY_FORM);
      setShowCreateForm(false);
      await fetchUsers();
    } catch (err) {
      setCreateError(getErrorMessage(err, 'Failed to create user.'));
    } finally {
      setCreating(false);
    }
  };

  const handleDeactivateUser = async (user) => {
    setDeactivateError('');
    setDeactivateSuccess('');

    const confirmed = window.confirm(
      `Deactivate ${getDisplayName(user)} (${user.email})? They will no longer be able to log in.`,
    );
    if (!confirmed) {
      return;
    }

    setDeactivatingUserId(user.id);

    try {
      await deactivateUser(user.id);
      setDeactivateSuccess(`${getDisplayName(user)} has been deactivated.`);
      await fetchUsers();
    } catch (err) {
      setDeactivateError(getErrorMessage(err, 'Failed to deactivate user.'));
    } finally {
      setDeactivatingUserId('');
    }
  };

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
          <p className="users-subtitle">Manage internal dashboard users</p>
        </div>
        <div className="users-header-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setShowCreateForm((prev) => !prev);
              setCreateError('');
              setCreateSuccess('');
            }}
          >
            {showCreateForm ? 'Cancel' : 'Create User'}
          </button>
          <button type="button" className="users-refresh" onClick={fetchUsers} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {showCreateForm && (
        <section className="users-section">
          <h2>Create User</h2>
          <form className="users-create-form" onSubmit={handleCreateUser}>
            <label htmlFor="name">Name</label>
            <input
              id="name"
              name="name"
              type="text"
              value={form.name}
              onChange={handleFormChange}
              placeholder="Full name"
              required
            />

            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleFormChange}
              placeholder="user@example.com"
              required
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              value={form.password}
              onChange={handleFormChange}
              placeholder="Minimum 8 characters"
              minLength={8}
              required
            />

            <label htmlFor="role">Role</label>
            <select id="role" name="role" value={form.role} onChange={handleFormChange} required>
              <option value="AGENT">AGENT</option>
              <option value="ADMIN">ADMIN</option>
            </select>

            {createError && <p className="users-error">{createError}</p>}
            {createSuccess && <p className="profile-success">{createSuccess}</p>}

            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? 'Creating User...' : 'Create User'}
            </button>
          </form>
        </section>
      )}

      {!showCreateForm && createSuccess && <p className="profile-success">{createSuccess}</p>}
      {deactivateSuccess && <p className="profile-success">{deactivateSuccess}</p>}
      {deactivateError && <p className="users-error">{deactivateError}</p>}

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
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const isActive = user.is_active !== false;
                const isSelf = user.id === currentUserId;
                const canDeactivate = isActive && !isSelf;

                return (
                <tr key={user.id}>
                  <td className="users-name">{getDisplayName(user)}</td>
                  <td>{user.email}</td>
                  <td>
                    <span className={`users-role-badge users-role-${user.role?.toLowerCase()}`}>
                      {user.role}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`users-status-badge ${
                        isActive ? 'users-status-active' : 'users-status-inactive'
                      }`}
                    >
                      {isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>{formatDate(user.created_at)}</td>
                  <td>
                    {canDeactivate ? (
                      <button
                        type="button"
                        className="btn-secondary users-deactivate-button"
                        onClick={() => handleDeactivateUser(user)}
                        disabled={deactivatingUserId === user.id}
                      >
                        {deactivatingUserId === user.id ? 'Deactivating...' : 'Deactivate'}
                      </button>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Users;
