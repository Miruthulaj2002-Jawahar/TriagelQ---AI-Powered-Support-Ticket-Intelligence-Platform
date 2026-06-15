import { useEffect, useState } from 'react';
import { getCurrentUser } from '../api/api.js';

export function useUserRole() {
  const [role, setRole] = useState(localStorage.getItem('role') || '');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((response) => {
        if (!active) {
          return;
        }
        setRole(response.data.role);
        localStorage.setItem('role', response.data.role);
      })
      .catch(() => {
        if (active) {
          setRole(localStorage.getItem('role') || '');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return {
    role,
    loading,
    isAdmin: role === 'ADMIN',
    isAgent: role === 'AGENT',
  };
}
