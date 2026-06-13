import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';
const TOKEN_KEY = 'token';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const setToken = (token) => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const getToken = () => {
  return localStorage.getItem(TOKEN_KEY);
};

export const clearToken = () => {
  localStorage.removeItem(TOKEN_KEY);
};

export const loginUser = async (email, password) => {
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);

  const response = await api.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  setToken(response.data.access_token);
  return response.data;
};

/** @deprecated Use loginUser */
export const login = loginUser;

export const getCurrentUser = () => api.get('/auth/me');

/** @deprecated Use getCurrentUser */
export const getMe = getCurrentUser;

export const changePassword = (currentPassword, newPassword) =>
  api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });

export const getTickets = () => api.get('/tickets');

export const createTicket = (ticketData) => api.post('/tickets', ticketData);

export const getTicketById = (ticketId) => api.get(`/tickets/${ticketId}`);

/** @deprecated Use getTicketById */
export const getTicket = getTicketById;

export const updateTicket = (id, ticketData) => api.put(`/tickets/${id}`, ticketData);

export const deleteTicket = (id) => api.delete(`/tickets/${id}`);

export const getAnalyticsSummary = () => api.get('/analytics/summary');

export const getUsers = () => api.get('/users');

export default api;
