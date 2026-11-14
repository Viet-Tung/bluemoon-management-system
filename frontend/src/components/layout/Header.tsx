import React, { useState } from 'react';
import { Menu, LogOut, KeyRound, ChevronDown, UserCircle2, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';
import { RoleCode } from '../../types';

interface HeaderProps {
  onToggleSidebar: () => void;
  onChangePassword: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, onChangePassword }) => {
  const { user, role, logout, switchDemoUser } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const rolesList: { code: RoleCode; label: string; badge: string }[] = [
    { code: 'ADMIN', label: 'Trưởng BQT (Admin)', badge: 'Toàn quyền' },
    { code: 'ACCOUNTANT', label: 'Kế toán viên', badge: 'Tài chính' },
    { code: 'TREASURER', label: 'Thủ quỹ', badge: 'Quầy thu' },
    { code: 'RESIDENT', label: 'Cư dân (Căn B1204)', badge: 'Portal' },
  ];

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
            Chung cư BlueMoon v1.0
          </span>
        </div>
      </div>

      {/* Right side: Demo Role Switcher & User Profile */}
      <div className="flex items-center gap-4">
        {/* Quick Demo Switcher */}
        <div className="hidden lg:flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl text-xs">
          <div className="flex items-center gap-1 text-[11px] font-bold text-slate-500 px-2 py-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            <span>Thử vai trò:</span>
          </div>
          {rolesList.map((r) => (
            <button
              key={r.code}
              onClick={() => switchDemoUser(r.code)}
              className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                role === r.code
                  ? 'bg-white text-blue-700 font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              {r.code === 'ADMIN'
                ? 'BQT'
                : r.code === 'ACCOUNTANT'
                ? 'Kế toán'
                : r.code === 'TREASURER'
                ? 'Thủ quỹ'
                : 'Cư dân'}
            </button>
          ))}
        </div>

        {/* User Profile Menu */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2.5 p-1.5 hover:bg-slate-100 rounded-xl transition text-left"
          >
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white font-bold text-xs shadow-xs">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="hidden sm:block text-xs">
              <p className="font-semibold text-slate-800 leading-tight truncate max-w-[140px]">
                {user?.full_name}
              </p>
              <div className="mt-0.5">
                <Badge size="sm" variant="info">
                  {user?.role?.name || role}
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

                {/* Mobile role switcher inside dropdown */}
                <div className="p-2 lg:hidden border-b border-slate-100">
                  <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-2 py-1">
                    Đổi vai trò thử nghiệm
                  </p>
                  <div className="grid grid-cols-2 gap-1 mt-1">
                    {rolesList.map((r) => (
                      <button
                        key={r.code}
                        onClick={() => {
                          switchDemoUser(r.code);
                          setDropdownOpen(false);
                        }}
                        className={`text-left px-2 py-1.5 rounded-lg text-xs font-medium ${
                          role === r.code ? 'bg-blue-50 text-blue-700 font-bold' : 'hover:bg-slate-100'
                        }`}
                      >
                        {r.code}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-1">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onChangePassword();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-xl transition"
                  >
                    <KeyRound className="w-4 h-4 text-slate-400" />
                    <span>Đổi mật khẩu cá nhân</span>
                  </button>
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 rounded-xl transition"
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
