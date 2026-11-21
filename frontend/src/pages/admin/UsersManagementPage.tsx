import React, { useEffect, useState, useCallback } from 'react';
import {
  UserCog,
  Plus,
  RefreshCw,
  AlertCircle,
  Lock,
  Unlock,
  KeyRound,
  ShieldCheck,
  CheckCircle,
  Search,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { User, Role } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const UsersManagementPage: React.FC = () => {
  const { success, error: toastError } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [searchKw, setSearchKw] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');

  // Create User Modal
  const [createOpen, setCreateOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newRoleId, setNewRoleId] = useState<number>(2); // Default to ACCOUNTANT

  // Temp Password Modal
  const [tempPasswordResult, setTempPasswordResult] = useState<{
    username: string;
    fullName: string;
    temporaryPassword: string;
    isReset?: boolean;
  } | null>(null);

  // Change Role Modal
  const [changeRoleOpen, setChangeRoleOpen] = useState(false);
  const [targetUser, setTargetUser] = useState<User | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<number>(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [userPage, roleList] = await Promise.all([
        ApiClient.getUsers({ page: 1, page_size: 100 }),
        ApiClient.getRoles(),
      ]);
      setUsers(userPage.items || []);
      setRoles(roleList || []);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách tài khoản từ máy chủ Backend.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [toastError]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await ApiClient.createUser({
        username: newUsername.trim(),
        full_name: newFullName.trim(),
        role_id: Number(newRoleId),
        email: newEmail.trim() || undefined,
        phone: newPhone.trim() || undefined,
      });

      setCreateOpen(false);
      setTempPasswordResult({
        username: result.username,
        fullName: result.full_name,
        temporaryPassword: result.temporary_password,
        isReset: false,
      });

      success(`Tạo tài khoản "${result.username}" thành công!`);
      setNewUsername('');
      setNewFullName('');
      setNewEmail('');
      setNewPhone('');
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleToggleLock = async (u: User) => {
    try {
      if (u.is_active) {
        if (!window.confirm(`Bạn có chắc muốn khóa tài khoản "${u.username}"?`)) return;
        await ApiClient.lockUser(u.id);
        success(`Đã khóa tài khoản "${u.username}" thành công!`);
      } else {
        await ApiClient.unlockUser(u.id);
        success(`Đã mở khóa tài khoản "${u.username}" thành công!`);
      }
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleResetPassword = async (u: User) => {
    if (!window.confirm(`Bạn có chắc muốn cấp lại mật khẩu tạm thời cho tài khoản "${u.username}"?`)) {
      return;
    }
    try {
      const res = await ApiClient.resetUserPassword(u.id);
      setTempPasswordResult({
        username: u.username,
        fullName: u.full_name,
        temporaryPassword: res.temporary_password,
        isReset: true,
      });
      success(`Đã đặt lại mật khẩu cho "${u.username}" thành công!`);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleChangeRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUser) return;
    try {
      await ApiClient.setUserRole(targetUser.id, Number(selectedRoleId));
      success(`Đã cập nhật vai trò cho người dùng "${targetUser.username}" thành công!`);
      setChangeRoleOpen(false);
      setTargetUser(null);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchKw =
      u.username.toLowerCase().includes(searchKw.toLowerCase()) ||
      u.full_name.toLowerCase().includes(searchKw.toLowerCase()) ||
      (u.email && u.email.toLowerCase().includes(searchKw.toLowerCase()));
    const matchRole = roleFilter === 'ALL' || u.role.code === roleFilter;
    return matchKw && matchRole;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <UserCog className="w-6 h-6 text-blue-600" />
            <span>Quản trị Tài khoản & Phân quyền RBAC (Sprint 1: US-30, US-31)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Quản lý tài khoản Ban Quản Trị, Kế toán, Thủ quỹ; phân vai trò và kiểm soát khóa/mở khóa tức thì.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            isLoading={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setCreateOpen(true)}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Tạo tài khoản mới
          </Button>
        </div>
      </div>

      {/* Backend Connection Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Lỗi kết nối Backend</p>
              <p className="text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={loadData}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
        <Input
          placeholder="Tìm theo tên đăng nhập, họ tên, email..."
          value={searchKw}
          onChange={(e) => setSearchKw(e.target.value)}
          icon={<Search className="w-4 h-4" />}
        />

        <div>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả vai trò</option>
            <option value="ADMIN">Ban Quản Trị (ADMIN)</option>
            <option value="ACCOUNTANT">Kế toán viên (ACCOUNTANT)</option>
            <option value="TREASURER">Thủ quỹ (TREASURER)</option>
            <option value="RESIDENT">Cư dân (RESIDENT)</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh sách tài khoản hệ thống</h3>
          <span className="text-xs text-slate-500">Mã hóa mật khẩu chuẩn Bcrypt rounds ≥ 12 (US-44)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Tên đăng nhập</th>
                <th className="py-3 px-4">Họ và tên</th>
                <th className="py-3 px-4">Email / SĐT</th>
                <th className="py-3 px-4">Vai trò (Role)</th>
                <th className="py-3 px-4">Đăng nhập gần nhất</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải dữ liệu người dùng...' : 'Không có tài khoản nào phù hợp.'}
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-700">{u.username}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">{u.full_name}</td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <p>{u.email || '---'}</p>
                      {u.phone && <p className="text-[11px] text-slate-400 font-mono">{u.phone}</p>}
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge variant="info" size="sm">
                        {u.role.name}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      {u.last_login_at
                        ? new Date(u.last_login_at).toLocaleString('vi-VN')
                        : 'Chưa đăng nhập'}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge variant={u.is_active ? 'success' : 'danger'} dot size="sm">
                        {u.is_active ? 'Hoạt động' : 'Đã khóa'}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {u.role.code !== 'RESIDENT' && (
                          <button
                            onClick={() => {
                              setTargetUser(u);
                              setSelectedRoleId(u.role.id);
                              setChangeRoleOpen(true);
                            }}
                            className="p-1.5 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                            title="Gán vai trò (US-31)"
                          >
                            <ShieldCheck className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => handleResetPassword(u)}
                          className="p-1.5 text-slate-600 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition"
                          title="Cấp lại mật khẩu tạm (US-29, US-30)"
                        >
                          <KeyRound className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleToggleLock(u)}
                          className={`p-1.5 rounded-lg transition ${
                            u.is_active
                              ? 'text-rose-600 hover:bg-rose-50'
                              : 'text-emerald-600 hover:bg-emerald-50'
                          }`}
                          title={u.is_active ? 'Khóa tài khoản (US-30)' : 'Mở khóa tài khoản (US-30)'}
                        >
                          {u.is_active ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Tạo tài khoản mới */}
      <Modal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Tạo tài khoản nhân sự mới (US-30)"
        description="Đăng ký tài khoản cho Ban Quản Trị, Kế toán hoặc Thủ quỹ. Mật khẩu tạm thời sẽ được tự động sinh."
      >
        <form onSubmit={handleCreateUser} className="space-y-4">
          <Input
            label="Tên đăng nhập (Username)"
            placeholder="Ví dụ: ketoan_02, thuquy_02..."
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            required
          />

          <Input
            label="Họ và tên đầy đủ"
            placeholder="Ví dụ: Trần Thị Mai..."
            value={newFullName}
            onChange={(e) => setNewFullName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Email liên hệ"
              type="email"
              placeholder="mai.tran@bluemoon.vn"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
            />
            <Input
              label="Số điện thoại"
              placeholder="0987654321"
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Vai trò nhân sự</label>
            <select
              value={newRoleId}
              onChange={(e) => setNewRoleId(Number(e.target.value))}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              {roles
                .filter((r) => r.code !== 'RESIDENT')
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.code})
                  </option>
                ))}
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setCreateOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Xác nhận tạo tài khoản
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal Hiển thị Mật khẩu tạm thời */}
      {tempPasswordResult && (
        <Modal
          isOpen={true}
          onClose={() => setTempPasswordResult(null)}
          title={tempPasswordResult.isReset ? 'Cấp lại mật khẩu thành công!' : 'Tạo tài khoản thành công!'}
          description="Vui lòng sao chép và bàn giao mật khẩu an toàn cho người dùng."
        >
          <div className="space-y-4">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs text-emerald-900 flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">
                  Tài khoản: {tempPasswordResult.username} ({tempPasswordResult.fullName})
                </p>
                <p className="mt-0.5">
                  {tempPasswordResult.isReset
                    ? 'Mật khẩu cũ đã bị vô hiệu hóa.'
                    : 'Tài khoản đã sẵn sàng đăng nhập.'}
                </p>
              </div>
            </div>

            <div className="p-4 bg-slate-900 text-white rounded-2xl space-y-2 text-xs">
              <span className="text-slate-400">Mật khẩu tạm thời mới cấp:</span>
              <div className="font-mono font-bold text-emerald-400 text-base bg-slate-800 p-2.5 rounded-xl text-center select-all">
                {tempPasswordResult.temporaryPassword}
              </div>
              <p className="text-[10px] text-slate-400 italic pt-1">
                * Hệ thống sẽ tự động yêu cầu người dùng thay đổi mật khẩu ở lần đăng nhập đầu tiên (US-29, AC-29.2).
              </p>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="primary" onClick={() => setTempPasswordResult(null)}>
                Đã sao chép & Đóng
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Thay đổi vai trò (US-31) */}
      <Modal
        isOpen={changeRoleOpen}
        onClose={() => setChangeRoleOpen(false)}
        title="Gán vai trò người dùng (US-31)"
        description={`Cập nhật vai trò phân quyền cho tài khoản ${targetUser?.username}.`}
      >
        <form onSubmit={handleChangeRole} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Vai trò mới</label>
            <select
              value={selectedRoleId}
              onChange={(e) => setSelectedRoleId(Number(e.target.value))}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              {roles
                .filter((r) => r.code !== 'RESIDENT')
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.code})
                  </option>
                ))}
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setChangeRoleOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Xác nhận thay đổi
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
