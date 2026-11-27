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
          {mustChangePassword ? (
            <div className="bg-white border border-amber-200 rounded-2xl p-6 text-xs text-slate-700 shadow-xs">
              <p className="font-bold text-slate-900">Yêu cầu đổi mật khẩu lần đầu</p>
              <p className="mt-1 text-slate-600">
                Vui lòng hoàn tất đổi mật khẩu tạm thời để kích hoạt tài khoản và truy cập dữ liệu hệ thống.
              </p>
            </div>
          ) : (
            <Outlet />
          )}
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
