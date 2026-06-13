import { useEffect, useState } from 'react';
import { getMe } from '../api/api.js';
import './Profile.css';

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function getErrorMessage(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return 'Failed to load profile.';
}

function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProfile = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await getMe();
        setUser(response.data);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, []);

  return (
    <div className="profile-page">
      <h1>Profile</h1>
      <p className="profile-subtitle">Your account information</p>

      {loading && <p className="profile-message">Loading profile...</p>}
      {!loading && error && <p className="profile-error">{error}</p>}

      {!loading && !error && user && (
        <dl className="profile-details">
          <div className="profile-row">
            <dt>Name</dt>
            <dd>{user.full_name}</dd>
          </div>
          <div className="profile-row">
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div className="profile-row">
            <dt>Role</dt>
            <dd>{user.role}</dd>
          </div>
          <div className="profile-row">
            <dt>Status</dt>
            <dd>{user.is_active ? 'Active' : 'Inactive'}</dd>
          </div>
          <div className="profile-row">
            <dt>Created At</dt>
            <dd>{formatDate(user.created_at)}</dd>
          </div>
        </dl>
      )}
    </div>
  );
}

export default Profile;
