import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('infrascan_token'));
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('infrascan_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  // Helper for authenticated fetch
  const authFetch = async (url, options = {}) => {
    const headers = { ...options.headers };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      logout();
    }
    return res;
  };

  useEffect(() => {
    if (token) {
      fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => {
          if (res.ok) {
            return res.json();
          } else {
            throw new Error('Session invalid');
          }
        })
        .then(userData => {
          setUser(userData);
          localStorage.setItem('infrascan_user', JSON.stringify(userData));
          setLoading(false);
        })
        .catch(() => {
          logout();
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (username, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    localStorage.setItem('infrascan_token', data.access_token);
    localStorage.setItem('infrascan_user', JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const register = async (username, email, password, full_name) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, full_name })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Registration failed');
    }
    return data;
  };

  const logout = () => {
    localStorage.removeItem('infrascan_token');
    localStorage.removeItem('infrascan_user');
    setToken(null);
    setUser(null);
  };

  const updateProfile = (updatedUser) => {
    setUser(updatedUser);
    localStorage.setItem('infrascan_user', JSON.stringify(updatedUser));
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        role: user?.role,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
        loading,
        login,
        register,
        logout,
        authFetch,
        updateProfile
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
