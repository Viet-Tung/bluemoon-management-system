import React, { useEffect, useState } from 'react';
import { UserCog, ShieldCheck, Lock, Unlock, KeyRound } from 'lucide-react';
import { ApiClient } from '../../api';
import { User } from '../../types';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useToast } from '../../context/ToastContext';

export const UsersManagementPage: React.FC = () => {
  const { success, error } = useToast();
  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await ApiClient.getUsers();
      setUsers(data);
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleToggleLock = async (u: User) => {
    try {
      await ApiClient.toggleUserStatus(u.id);
      success(`Đã ${u.is_active ? 'khóa' : 'mở khóa'} tài khoản ${u.username} thành công!`);
      loadUsers();
    } catch (err: any) {
      error(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <UserCog className="w-6 h-6 text-blue-600" />
          <span>Quản lý Tài khoản & Phân quyền RBAC (US-30, US-31)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Quản lý tài khoản Ban Quản Trị, Kế toán, Thủ quỹ và Cư dân; kiểm soát trạng thái khóa/mở khóa tức thì (AC-30.1).
        </p>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh sách tài khoản trong hệ thống</h3>
          <span className="text-xs text-slate-500">Mã hóa mật khẩu chuẩn Bcrypt rounds $\ge$ 12 (US-44)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Tên đăng nhập</th>
                <th className="py-3 px-4">Họ và tên</th>
                <th className="py-3 px-4">Email / Số điện thoại</th>
                <th className="py-3 px-4">Vai trò (Role)</th>
                <th className="py-3 px-4">Đăng nhập gần nhất</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="py-3.5 px-4 font-mono font-bold text-blue-700">{u.username}</td>
                  <td className="py-3.5 px-4 font-semibold text-slate-900">{u.full_name}</td>
                  <td className="py-3.5 px-4 text-slate-600">
                    <p>{u.email || '---'}</p>
                    <p className="text-[11px] text-slate-400 font-mono">{u.phone}</p>
                  </td>
                  <td className="py-3.5 px-4">
                    <Badge variant="info" size="sm">
                      {u.role.name}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleString('vi-VN') : 'Chưa đăng nhập'}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <Badge variant={u.is_active ? 'success' : 'danger'} dot size="sm">
                      {u.is_active ? 'Hoạt động' : 'Đã khóa'}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Button
                      size="sm"
                      variant={u.is_active ? 'danger' : 'success'}
                      onClick={() => handleToggleLock(u)}
                      icon={u.is_active ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
                    >
                      {u.is_active ? 'Khóa tài khoản' : 'Mở khóa'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
