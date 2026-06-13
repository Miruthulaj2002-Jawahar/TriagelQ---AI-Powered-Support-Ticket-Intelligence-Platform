import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './components/AppLayout.jsx';
import Analytics from './pages/Analytics.jsx';
import CreateTicket from './pages/CreateTicket.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Login from './pages/Login.jsx';
import TicketDetail from './pages/TicketDetail.jsx';
import Tickets from './pages/Tickets.jsx';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/tickets/:id" element={<TicketDetail />} />
          <Route path="/tickets" element={<Tickets />} />
          <Route path="/create-ticket" element={<CreateTicket />} />
          <Route path="/analytics" element={<Analytics />} />
        </Route>

        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
