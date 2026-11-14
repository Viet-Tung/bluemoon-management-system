import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ChangePasswordModal } from '../../pages/auth/ChangePasswordModal';
import { useAuth } from '../../context/AuthContext';

export const AppShell: React.FC = () => {
  const { user } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  const mustChangePassword = Boolean(user?.must_change_password);

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />

      {/* Main Content Area */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${
          collapsed ? 'ml-20' : 'ml-64'
        }`}
      >
        <Header
          onToggleSidebar={() => setCollapsed(!collapsed)}
          onChangePassword={() => setChangePasswordOpen(true)}
        />

        <main className="flex-1 p-6 sm:p-8 max-w-7xl w-full mx-auto animate-in fade-in duration-200">
          <Outlet />
        </main>
      </div>

      {/* Modal Change Password */}
      <ChangePasswordModal
        isOpen={changePasswordOpen || mustChangePassword}
        onClose={() => setChangePasswordOpen(false)}
        isFirstLogin={mustChangePassword}
      />
    </div>
  );
};
