import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  Users,
  CreditCard,
  Receipt,
  PiggyBank,
  FileText,
  UserCheck,
  ShieldCheck,
  History,
  Database,
  Building,
  UserCog,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed }) => {
  const { hasRole, role } = useAuth();

  const navGroups = [
    {
      title: 'Tổng quan',
      items: [
        {
          name: 'Dashboard',
          path: '/dashboard',
          icon: LayoutDashboard,
          roles: ['ADMIN', 'ACCOUNTANT', 'TREASURER'],
        },
      ],
    },
    {
      title: 'Cư dân & Căn hộ',
      items: [
        {
          name: 'Căn hộ & Hộ gia đình',
          path: '/apartments',
          icon: Building2,
          roles: ['ADMIN', 'ACCOUNTANT'],
        },
        {
          name: 'Nhân khẩu & Tạm trú',
          path: '/residents',
          icon: Users,
          roles: ['ADMIN', 'ACCOUNTANT'],
        },
      ],
    },
    {
      title: 'Thu phí & Tài chính',
      items: [
        {
          name: 'Quầy thu ngân',
          path: '/cashier',
          icon: CreditCard,
          roles: ['TREASURER', 'ADMIN'],
          badge: 'Nhanh',
        },
        {
          name: 'Danh mục biểu phí',
          path: '/fee-catalog',
          icon: FileText,
          roles: ['ACCOUNTANT', 'ADMIN'],
        },
        {
          name: 'Kỳ thu & Tính phí',
          path: '/billing',
          icon: Receipt,
          roles: ['ACCOUNTANT', 'ADMIN'],
        },
        {
          name: 'Theo dõi công nợ',
          path: '/debts',
          icon: History,
          roles: ['ACCOUNTANT', 'ADMIN'],
        },
        {
          name: 'Quỹ tự nguyện',
          path: '/donations',
          icon: PiggyBank,
          roles: ['TREASURER', 'ACCOUNTANT', 'ADMIN'],
        },
      ],
    },
    {
      title: 'Cổng Cư Dân',
      items: [
        {
          name: 'Hồ sơ Hộ gia đình',
          path: '/portal/household',
          icon: Building,
          roles: ['RESIDENT'],
        },
        {
          name: 'Công nợ & Đóng phí',
          path: '/portal/finances',
          icon: CreditCard,
          roles: ['RESIDENT'],
        },
      ],
    },
    {
      title: 'Quản trị hệ thống',
      items: [
        {
          name: 'Duyệt đề nghị cư dân',
          path: '/admin/change-requests',
          icon: UserCheck,
          roles: ['ADMIN'],
        },
        {
          name: 'Tài khoản & Phân quyền',
          path: '/admin/users',
          icon: UserCog,
          roles: ['ADMIN'],
        },
        {
          name: 'Nhật ký Audit Log',
          path: '/admin/audit-logs',
          icon: ShieldCheck,
          roles: ['ADMIN'],
        },
        {
          name: 'Sao lưu CSDL',
          path: '/admin/backups',
          icon: Database,
          roles: ['ADMIN'],
        },
      ],
    },
  ];

  return (
    <aside
      className={`fixed top-0 left-0 bottom-0 z-40 bg-slate-900 text-slate-300 border-r border-slate-800 transition-all duration-300 flex flex-col ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-slate-800 gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-black text-lg shadow-md shadow-blue-500/20 flex-shrink-0">
          BM
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-white tracking-tight truncate">BlueMoon</h1>
            <p className="text-[11px] text-slate-400 truncate">Quản lý Chung cư</p>
          </div>
        )}
      </div>

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {navGroups.map((group, gIdx) => {
          const visibleItems = group.items.filter((item) =>
            item.roles.some((r) => hasRole(r as any))
          );
          if (visibleItems.length === 0) return null;

          return (
            <div key={gIdx} className="space-y-1">
              {!collapsed && (
                <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                  {group.title}
                </p>
              )}
              {visibleItems.map((item, iIdx) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={iIdx}
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                        isActive
                          ? 'bg-blue-600 text-white font-semibold shadow-sm shadow-blue-500/20'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                      }`
                    }
                    title={collapsed ? item.name : undefined}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    {!collapsed && <span className="truncate flex-1">{item.name}</span>}
                    {!collapsed && item.badge && (
                      <span className="text-[9px] font-bold bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-md">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Bottom Role Info */}
      <div className="p-3 border-t border-slate-800">
        {!collapsed ? (
          <div className="bg-slate-800/60 rounded-xl p-2.5 flex items-center justify-between text-xs">
            <div className="truncate">
              <p className="text-[11px] text-slate-400">Đang truy cập với vai trò</p>
              <p className="text-white font-semibold truncate mt-0.5">{role}</p>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        ) : (
          <div className="flex justify-center" title={`Vai trò: ${role}`}>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        )}
      </div>
    </aside>
  );
};
