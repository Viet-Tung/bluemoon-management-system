import React, { useState } from 'react';
import { Menu, LogOut, KeyRound, ChevronDown } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';

interface HeaderProps {
  onToggleSidebar: () => void;
  onChangePassword: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, onChangePassword }) => {
  const { user, role, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const getRoleDisplayName = (code?: string) => {
    switch (code) {
      case 'ADMIN':
        return 'Ban Quản Trị (Admin)';
      case 'ACCOUNTANT':
        return 'Kế toán viên';
      case 'TREASURER':
        return 'Thủ quỹ';
      case 'RESIDENT':
        return 'Cư dân';
      default:
        return code || 'Người dùng';
    }
  };

  return (
    <header className="sticky top-0 z-30 h-16 bg-white/90 backdrop-blur-md border-b border-slate-200 px-6 flex items-center justify-between">
      {/* Left side */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleSidebar}
          className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition"
          title="Thu gọn / Mở rộng Menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <span className="text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md">
            Chung cư BlueMoon v1.0 • Sprint 1
          </span>
        </div>
      </div>

      {/* Right side: Authenticated User Profile */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2.5 p-1.5 hover:bg-slate-100 rounded-xl transition text-left"
          >
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white font-bold text-xs shadow-xs">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="hidden sm:block text-xs">
              <p className="font-semibold text-slate-800 leading-tight truncate max-w-[160px]">
                {user?.full_name || user?.username}
              </p>
              <div className="mt-0.5">
                <Badge size="sm" variant="info">
                  {user?.role?.name || getRoleDisplayName(role || undefined)}
                </Badge>
              </div>
            </div>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </button>

          {/* Dropdown popup */}
          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
              <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-4 py-3 border-b border-slate-100">
                  <p className="text-xs text-slate-500">Tài khoản đăng nhập</p>
                  <p className="text-sm font-bold text-slate-800">{user?.username}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{user?.email || 'Chưa cập nhật email'}</p>
                </div>

                <div className="p-2 space-y-1">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onChangePassword();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:text-blue-600 hover:bg-blue-50/50 rounded-xl transition text-left"
                  >
                    <KeyRound className="w-4 h-4 text-slate-400" />
                    <span>Đổi mật khẩu tài khoản</span>
                  </button>

                  <button
                    onClick={async () => {
                      setDropdownOpen(false);
                      await logout();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 rounded-xl transition text-left"
                  >
                    <LogOut className="w-4 h-4 text-rose-500" />
                    <span>Đăng xuất hệ thống</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
