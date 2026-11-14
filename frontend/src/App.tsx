import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/auth/LoginPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { ApartmentsPage } from './pages/apartments/ApartmentsPage';
import { ResidentsPage } from './pages/residents/ResidentsPage';
import { CashierPage } from './pages/cashier/CashierPage';
import { FeeCatalogPage } from './pages/billing/FeeCatalogPage';
import { BillingPeriodsPage } from './pages/billing/BillingPeriodsPage';
import { DebtManagementPage } from './pages/cashier/DebtManagementPage';
import { DonationCampaignsPage } from './pages/donations/DonationCampaignsPage';
import { PortalHouseholdPage } from './pages/portal/PortalHouseholdPage';
import { PortalFinancesPage } from './pages/portal/PortalFinancesPage';
import { ChangeRequestsReviewPage } from './pages/admin/ChangeRequestsReviewPage';
import { UsersManagementPage } from './pages/admin/UsersManagementPage';
import { AuditLogsPage } from './pages/admin/AuditLogsPage';
import { SystemBackupPage } from './pages/admin/SystemBackupPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
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
        <Route path="apartments" element={<ApartmentsPage />} />
        <Route path="residents" element={<ResidentsPage />} />
        <Route path="cashier" element={<CashierPage />} />
        <Route path="fee-catalog" element={<FeeCatalogPage />} />
        <Route path="billing" element={<BillingPeriodsPage />} />
        <Route path="debts" element={<DebtManagementPage />} />
        <Route path="donations" element={<DonationCampaignsPage />} />

        {/* Resident Portal */}
        <Route path="portal/household" element={<PortalHouseholdPage />} />
        <Route path="portal/finances" element={<PortalFinancesPage />} />

        {/* Admin Management */}
        <Route path="admin/change-requests" element={<ChangeRequestsReviewPage />} />
        <Route path="admin/users" element={<UsersManagementPage />} />
        <Route path="admin/audit-logs" element={<AuditLogsPage />} />
        <Route path="admin/backups" element={<SystemBackupPage />} />

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
