import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import './AppLayout.css';

function AppLayout() {
  const role = localStorage.getItem('role');
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <header className="app-navbar">
        <div className="navbar-brand">TriageIQ</div>

        <nav className="navbar-links">
          {role === 'ADMIN' && (
            <>
              <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Dashboard
              </NavLink>
              <NavLink to="/tickets" end className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Tickets
              </NavLink>
              <NavLink to="/analytics" className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Analytics
              </NavLink>
              <NavLink to="/users" className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Users
              </NavLink>
              <NavLink to="/profile" className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Profile
              </NavLink>
            </>
          )}

          {role === 'AGENT' && (
            <>
              <NavLink to="/tickets" end className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Tickets
              </NavLink>
              <NavLink to="/create-ticket" className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Create Ticket
              </NavLink>
              <NavLink to="/profile" className={({ isActive }) => (isActive ? 'active' : undefined)}>
                Profile
              </NavLink>
            </>
          )}
        </nav>

        <button type="button" className="logout-button" onClick={handleLogout}>
          Logout
        </button>
      </header>

      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
