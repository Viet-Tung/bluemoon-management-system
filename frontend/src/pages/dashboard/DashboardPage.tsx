import React, { useEffect, useState, useCallback } from 'react';
import {
  Building2,
  Users,
  FileText,
  UserCog,
  Database,
  ShieldCheck,
  RefreshCw,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { ApiClient } from '../../api';
import { AuditLog, BackupJob } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Sprint 1 Statistics
  const [stats, setStats] = useState({
    totalApartments: 0,
    totalHouseholds: 0,
    activeFeeTypes: 0,
    totalUsers: 0,
  });

  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([]);
  const [recentBackups, setRecentBackups] = useState<BackupJob[]>([]);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [aptRes, hhRes, feeRes, userRes, logsRes, backupsRes] = await Promise.all([
        ApiClient.getApartments({ page: 1, page_size: 1 }),
        ApiClient.getHouseholds({ page: 1, page_size: 1 }),
        ApiClient.getFeeTypes({ page: 1, page_size: 1, status: 'ACTIVE' }),
        ApiClient.getUsers({ page: 1, page_size: 1 }),
        ApiClient.getAuditLogs({ page: 1, page_size: 5 }).catch(() => ({ items: [] })),
        ApiClient.getBackupJobs({ page: 1, page_size: 3 }).catch(() => ({ items: [] })),
      ]);

      setStats({
        totalApartments: aptRes.total || 0,
        totalHouseholds: hhRes.total || 0,
        activeFeeTypes: feeRes.total || 0,
        totalUsers: userRes.total || 0,
      });

      setRecentLogs(logsRes.items || []);
      setRecentBackups(backupsRes.items || []);
    } catch (err: any) {
      setErrorMessage(
        err.message ||
          'Không thể kết nối đến máy chủ Backend (http://localhost:8000). Vui lòng kiểm tra dịch vụ Backend.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  return (
    <div className="space-y-6">
      {/* Welcome Hero Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-3xl p-6 sm:p-8 text-white relative overflow-hidden shadow-xl">
        <div className="relative z-10 max-w-2xl">
          <span className="text-xs font-bold uppercase tracking-wider bg-white/10 px-3 py-1 rounded-full text-blue-200 backdrop-blur-xs">
            Hệ thống Quản lý Chung cư BlueMoon • Sprint 1
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-3">
            Xin chào, {user?.full_name || user?.username}!
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Hệ thống quản lý thông tin căn hộ, hồ sơ cư trú hộ gia đình, danh mục biểu phí và kiểm soát an toàn bảo mật.
          </p>

          <div className="flex flex-wrap gap-3 mt-6">
            <Link
              to="/apartments"
              className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition shadow-md shadow-blue-500/20"
            >
              <Building2 className="w-4 h-4" />
              <span>Quản lý Căn hộ & Hộ gia đình</span>
            </Link>
            <Link
              to="/fee-catalog"
              className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition backdrop-blur-xs"
            >
              <FileText className="w-4 h-4" />
              <span>Danh mục biểu phí</span>
            </Link>
          </div>
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
          <Button
            size="sm"
            variant="outline"
            onClick={fetchDashboardData}
            isLoading={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Thử lại
          </Button>
        </div>
      )}

      {/* KPI Cards: Sprint 1 Real Data */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Apartments */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Tổng số Căn hộ</span>
            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Building2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">
            {loading ? '...' : stats.totalApartments}
          </p>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
            <span>Dữ liệu vật lý (US-01)</span>
          </div>
        </div>

        {/* Total Households */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Hộ gia đình cư trú</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">
            {loading ? '...' : stats.totalHouseholds}
          </p>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
            <span>Đang theo dõi quản lý (US-01, US-02)</span>
          </div>
        </div>

        {/* Active Fee Types */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Danh mục Khoản thu</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">
            {loading ? '...' : stats.activeFeeTypes}
          </p>
          <div className="text-[11px] text-emerald-600 mt-1 flex items-center gap-1">
            <span>Khoản phí đang áp dụng (US-12)</span>
          </div>
        </div>

        {/* Total System Users */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Tài khoản Hệ thống</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <UserCog className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">
            {loading ? '...' : stats.totalUsers}
          </p>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
            <span>Phân quyền RBAC (US-30, US-31)</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Recent Backups & Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Audit Logs */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-800">Nhật ký Audit Log gần nhất (US-32)</h2>
            </div>
            <Link
              to="/admin/audit-logs"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>Xem tất cả</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {recentLogs.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">
                {loading ? 'Đang tải nhật ký...' : 'Chưa có thao tác nào được ghi nhận.'}
              </p>
            ) : (
              recentLogs.map((log) => (
                <div
                  key={log.id}
                  className="p-3 bg-slate-50 rounded-xl flex items-center justify-between text-xs"
                >
                  <div className="min-w-0 flex-1 pr-3">
                    <p className="font-mono font-bold text-blue-700 truncate">{log.action}</p>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">
                      {log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ''} - {log.reason || 'Thao tác hệ thống'}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono flex-shrink-0">
                    {new Date(log.created_at).toLocaleTimeString('vi-VN')}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Backups */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-800">Tiến trình Sao lưu CSDL (US-45)</h2>
            </div>
            <Link
              to="/admin/backups"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>Chi tiết sao lưu</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {recentBackups.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">
                {loading ? 'Đang tải thông tin sao lưu...' : 'Chưa có bản ghi sao lưu nào.'}
              </p>
            ) : (
              recentBackups.map((job) => (
                <div
                  key={job.id}
                  className="p-3 bg-slate-50 rounded-xl flex items-center justify-between text-xs"
                >
                  <div>
                    <span className="font-mono font-bold text-slate-800">Job #{job.id}</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {new Date(job.requested_at).toLocaleString('vi-VN')}
                    </p>
                  </div>
                  <Badge
                    variant={job.status === 'SUCCEEDED' ? 'success' : job.status === 'RUNNING' ? 'info' : 'warning'}
                    dot
                    size="sm"
                  >
                    {job.status}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
