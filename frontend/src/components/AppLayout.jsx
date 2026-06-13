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
              <NavLink to="/dashboard">Dashboard</NavLink>
              <NavLink to="/tickets">Tickets</NavLink>
              <NavLink to="/analytics">Analytics</NavLink>
            </>
          )}

          {role === 'AGENT' && (
            <>
              <NavLink to="/tickets">Tickets</NavLink>
              <NavLink to="/create-ticket">Create Ticket</NavLink>
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
