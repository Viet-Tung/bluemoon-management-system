import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, RoleCode } from '../types';
import { ApiClient } from '../api';

interface AuthContextType {
  user: User | null;
  role: RoleCode | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (...roles: RoleCode[]) => boolean;
  updateUser: (user: User) => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Validate session on initial load or page refresh
  const refreshUser = useCallback(async () => {
    const token = ApiClient.getToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await ApiClient.getMe();
      setUser(currentUser);
    } catch {
      // Token is invalid, expired, or backend rejected
      ApiClient.setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const result = await ApiClient.login(username, password);
      setUser(result.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await ApiClient.logout();
    } catch {
      // Swallowed: if server offline, still clear local token
    } finally {
      ApiClient.setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  const hasRole = (...roles: RoleCode[]) => {
    if (!user || !user.role) return false;
    return roles.includes(user.role.code);
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
        updateUser,
        refreshUser,
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
