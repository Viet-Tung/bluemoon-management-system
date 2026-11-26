import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/auth/LoginPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { ApartmentsPage } from './pages/apartments/ApartmentsPage';
import { ResidentsPage } from './pages/residents/ResidentsPage';
import { VehiclesPage } from './pages/vehicles/VehiclesPage';
import { FeeCatalogPage } from './pages/billing/FeeCatalogPage';
import { FeeExemptionsPage } from './pages/billing/FeeExemptionsPage';
import { BillingPage } from './pages/billing/BillingPage';
import { UsersManagementPage } from './pages/admin/UsersManagementPage';
import { AuditLogsPage } from './pages/admin/AuditLogsPage';
import { SystemBackupPage } from './pages/admin/SystemBackupPage';
import { RoleCode } from './types';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center text-white">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-xs text-slate-400 font-medium tracking-wide">Đang kiểm tra phiên đăng nhập...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

const RoleRoute: React.FC<{ roles: RoleCode[]; children: React.ReactNode }> = ({ roles, children }) => {
  const { hasRole, isLoading } = useAuth();

  if (isLoading) return null;

  if (!hasRole(...roles)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export const AppContent: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route
          path="apartments"
          element={
            <RoleRoute roles={['ADMIN', 'ACCOUNTANT']}>
              <ApartmentsPage />
            </RoleRoute>
          }
        />
        <Route
          path="residents"
          element={
            <RoleRoute roles={['ADMIN', 'ACCOUNTANT']}>
              <ResidentsPage />
            </RoleRoute>
          }
        />
        <Route
          path="vehicles"
          element={
            <RoleRoute roles={['ADMIN', 'ACCOUNTANT']}>
              <VehiclesPage />
            </RoleRoute>
          }
        />
        <Route
          path="fee-catalog"
          element={
            <RoleRoute roles={['ADMIN', 'ACCOUNTANT']}>
              <FeeCatalogPage />
            </RoleRoute>
          }
        />
        <Route
          path="fee-exemptions"
          element={
            <RoleRoute roles={['ADMIN', 'ACCOUNTANT']}>
              <FeeExemptionsPage />
            </RoleRoute>
          }
        />
        <Route
          path="billing"
          element={
            <RoleRoute roles={['ADMIN', 'ACCOUNTANT']}>
              <BillingPage />
            </RoleRoute>
          }
        />

        {/* Admin Management */}
        <Route
          path="admin/users"
          element={
            <RoleRoute roles={['ADMIN']}>
              <UsersManagementPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/audit-logs"
          element={
            <RoleRoute roles={['ADMIN']}>
              <AuditLogsPage />
            </RoleRoute>
          }
        />
        <Route
          path="admin/backups"
          element={
            <RoleRoute roles={['ADMIN']}>
              <SystemBackupPage />
            </RoleRoute>
          }
        />

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
};

export function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
