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
  Home,
  Car,
  Receipt,
  Search,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { ApiClient } from '../../api';
import { AuditLog, BackupJob } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';

export const DashboardPage: React.FC = () => {
  const { user, hasRole } = useAuth();

  const isAdmin = hasRole('ADMIN');
  const canManageProperty = hasRole('ADMIN', 'ACCOUNTANT');
  const isTreasurer = hasRole('TREASURER');
  const isResident = hasRole('RESIDENT');

  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [stats, setStats] = useState({
    totalApartments: 0,
    totalHouseholds: 0,
    activeFeeTypes: 0,
    totalVehicles: 0,
    totalBillingPeriods: 0,
    totalInvoices: 0,
    totalUsers: 0,
  });

  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([]);
  const [recentBackups, setRecentBackups] = useState<BackupJob[]>([]);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);

    if (isResident || isTreasurer || !canManageProperty) {
      setLoading(false);
      return;
    }

    try {
      const promises: Promise<any>[] = [
        ApiClient.getApartments({ page: 1, page_size: 1 }),
        ApiClient.getHouseholds({ page: 1, page_size: 1 }),
        ApiClient.getFeeTypes({ page: 1, page_size: 1, status: 'ACTIVE' }),
        ApiClient.getVehicles({ page: 1, page_size: 1, status: 'ACTIVE' }),
        ApiClient.getBillingPeriods({ page: 1, page_size: 1 }),
        ApiClient.getInvoices({ page: 1, page_size: 1 }),
      ];

      if (isAdmin) {
        promises.push(
          ApiClient.getUsers({ page: 1, page_size: 1 }),
          ApiClient.getAuditLogs({ page: 1, page_size: 5 }).catch(() => ({ items: [] })),
          ApiClient.getBackupJobs({ page: 1, page_size: 3 }).catch(() => ({ items: [] }))
        );
      }

      const results = await Promise.all(promises);
      const aptRes = results[0];
      const hhRes = results[1];
      const feeRes = results[2];
      const vehRes = results[3];
      const periodRes = results[4];
      const invRes = results[5];
      const userRes = isAdmin ? results[6] : { total: 0 };
      const logsRes = isAdmin ? results[7] : { items: [] };
      const backupsRes = isAdmin ? results[8] : { items: [] };

      setStats({
        totalApartments: aptRes.total || 0,
        totalHouseholds: hhRes.total || 0,
        activeFeeTypes: feeRes.total || 0,
        totalVehicles: vehRes.total || 0,
        totalBillingPeriods: periodRes.total || 0,
        totalInvoices: invRes.total || 0,
        totalUsers: userRes.total || 0,
      });

      if (isAdmin) {
        setRecentLogs(logsRes.items || []);
        setRecentBackups(backupsRes.items || []);
      }
    } catch (err: any) {
      setErrorMessage(
        err.message ||
          'Không thể kết nối đến máy chủ hệ thống. Vui lòng kiểm tra dịch vụ.'
      );
    } finally {
      setLoading(false);
    }
  }, [isAdmin, canManageProperty, isTreasurer, isResident]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  return (
    <div className="space-y-6">
      {/* Welcome Hero Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-3xl p-6 sm:p-8 text-white relative overflow-hidden shadow-xl">
        <div className="relative z-10 max-w-3xl">
          <span className="text-xs font-bold uppercase tracking-wider bg-white/10 px-3 py-1 rounded-full text-blue-200 backdrop-blur-xs">
            Hệ thống Quản lý Chung cư BlueMoon
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-3">
            Xin chào, {user?.full_name || user?.username}!
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Quản lý căn hộ, hồ sơ hộ gia đình & nhân khẩu, phương tiện gửi xe, danh mục biểu phí, miễn giảm và phát hành giấy báo nộp phí hàng tháng.
          </p>

          {canManageProperty && (
            <div className="flex flex-wrap gap-2.5 mt-6">
              <Link
                to="/apartments"
                className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition shadow-md shadow-blue-500/20"
              >
                <Building2 className="w-4 h-4" />
                <span>Căn hộ & Hộ gia đình</span>
              </Link>
              <Link
                to="/residents"
                className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition backdrop-blur-xs"
              >
                <Users className="w-4 h-4" />
                <span>Cư dân & Nhập Excel</span>
              </Link>
              <Link
                to="/vehicles"
                className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition backdrop-blur-xs"
              >
                <Car className="w-4 h-4" />
                <span>Phương tiện</span>
              </Link>
              <Link
                to="/fee-catalog"
                className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition backdrop-blur-xs"
              >
                <FileText className="w-4 h-4" />
                <span>Khoản thu & Miễn giảm</span>
              </Link>
              <Link
                to="/billing"
                className="inline-flex items-center gap-2 bg-emerald-500/90 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition shadow-md shadow-emerald-500/20"
              >
                <Receipt className="w-4 h-4" />
                <span>Kỳ thu & Giấy báo phí</span>
              </Link>
            </div>
          )}

          {isTreasurer && (
            <div className="mt-4 p-4 rounded-2xl bg-white/10 backdrop-blur-xs border border-white/20 text-xs text-blue-100 flex items-start gap-3">
              <Search className="w-5 h-5 text-blue-300 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-white">Không gian làm việc Thủ quỹ</p>
                <p className="mt-0.5 text-blue-200">
                  Bạn có thể sử dụng ô tìm kiếm nhanh trên thanh tiêu đề để tra cứu thông tin hộ gia đình, căn hộ, cư dân và biển số phương tiện.
                </p>
              </div>
            </div>
          )}

          {isResident && (
            <div className="mt-4 p-4 rounded-2xl bg-white/10 backdrop-blur-xs border border-white/20 text-xs text-blue-100 flex items-start gap-3">
              <Home className="w-5 h-5 text-blue-300 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-white">Cổng thông tin cư dân</p>
                <p className="mt-0.5 text-blue-200">
                  Bạn đang đăng nhập với tài khoản cư dân. Hãy liên hệ Ban Quản Trị nếu bạn cần hỗ trợ thông tin hoặc thay đổi hồ sơ cư trú.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Connection Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Lỗi kết nối máy chủ</p>
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

      {/* KPI Cards */}
      {canManageProperty && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
            <div className="text-[11px] text-slate-500 mt-1">Căn hộ trong tòa nhà</div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold">Hộ gia đình</span>
              <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Users className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-slate-900 font-mono">
              {loading ? '...' : stats.totalHouseholds}
            </p>
            <div className="text-[11px] text-slate-500 mt-1">Hộ gia đình đang quản lý</div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold">Phương tiện đang gửi</span>
              <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                <Car className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-slate-900 font-mono">
              {loading ? '...' : stats.totalVehicles}
            </p>
            <div className="text-[11px] text-slate-500 mt-1">Xe máy, ô tô, xe đạp</div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold">Khoản thu đang dùng</span>
              <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <FileText className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-slate-900 font-mono">
              {loading ? '...' : stats.activeFeeTypes}
            </p>
            <div className="text-[11px] text-emerald-600 mt-1">Biểu phí đang áp dụng</div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold">Kỳ thu phí</span>
              <div className="w-8 h-8 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
                <Receipt className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-slate-900 font-mono">
              {loading ? '...' : stats.totalBillingPeriods}
            </p>
            <div className="text-[11px] text-slate-500 mt-1">
              {loading ? '...' : `${stats.totalInvoices} giấy báo nộp phí`}
            </div>
          </div>

          {isAdmin && (
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold">Tài khoản Hệ thống</span>
                <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                  <UserCog className="w-4 h-4" />
                </div>
              </div>
              <p className="text-2xl font-bold text-slate-900 font-mono">
                {loading ? '...' : stats.totalUsers}
              </p>
              <div className="text-[11px] text-slate-500 mt-1">Tài khoản người dùng</div>
            </div>
          )}
        </div>
      )}

      {/* Two Column Layout: Recent Backups & Audit Logs (Admin only) */}
      {isAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Audit Logs */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-bold text-slate-800">Nhật ký hoạt động gần nhất</h2>
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
                        {log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ''} -{' '}
                        {log.reason || 'Thao tác hệ thống'}
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
                <h2 className="text-sm font-bold text-slate-800">Trạng thái sao lưu dữ liệu</h2>
              </div>
              <Link
                to="/admin/backups"
                className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                <span>Xem chi tiết</span>
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
                      <span className="font-mono font-bold text-slate-800">Bản sao lưu #{job.id}</span>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {new Date(job.requested_at).toLocaleString('vi-VN')}
                      </p>
                    </div>
                    <Badge
                      variant={
                        job.status === 'SUCCEEDED'
                          ? 'success'
                          : job.status === 'RUNNING'
                          ? 'info'
                          : 'warning'
                      }
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
      )}
    </div>
  );
};
