import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, RoleCode } from '../types';
import { ApiClient } from '../api';
import { INITIAL_USERS } from '../api/mockData';

interface AuthContextType {
  user: User | null;
  role: RoleCode | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: RoleCode[]) => boolean;
  switchDemoUser: (roleCode: RoleCode) => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem('bluemoon_current_user');
      if (saved) return JSON.parse(saved);
      // Default initial user is Admin for convenient demo
      return INITIAL_USERS[0];
    } catch {
      return INITIAL_USERS[0];
    }
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (user) {
      localStorage.setItem('bluemoon_current_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('bluemoon_current_user');
    }
  }, [user]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const result = await ApiClient.login(username, password);
      setUser(result.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    ApiClient.setToken(null);
    setUser(null);
  };

  const hasRole = (...roles: RoleCode[]) => {
    if (!user || !user.role) return false;
    return roles.includes(user.role.code);
  };

  const switchDemoUser = (roleCode: RoleCode) => {
    const demo = INITIAL_USERS.find((u) => u.role.code === roleCode);
    if (demo) {
      setUser(demo);
      ApiClient.setToken(`demo-token-${demo.id}`);
    }
  };

  const updateUser = (updated: User) => {
    setUser(updated);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role?.code || null,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        hasRole,
        switchDemoUser,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
