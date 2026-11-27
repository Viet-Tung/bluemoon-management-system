import React, { useEffect, useState, useCallback } from 'react';
import { ShieldCheck, Search, Eye, RefreshCw, AlertCircle, RotateCcw } from 'lucide-react';
import { ApiClient } from '../../api';
import { AuditLog } from '../../types';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 20;

const AUDIT_ACTION_OPTIONS = [
  'CHANGE_ROLE',
  'LOCK_USER',
  'UNLOCK_USER',
  'RESET_PASSWORD',
  'ACCESS_DENIED',
  'DEACTIVATE_HOUSEHOLD',
  'TRANSFER_APARTMENT',
  'CHANGE_HEAD',
  'CREATE_RESIDENT',
  'UPDATE_RESIDENT',
  'DELETE_RESIDENT',
  'IMPORT_EXCEL',
  'CREATE_VEHICLE',
  'UPDATE_VEHICLE',
  'UNREGISTER_VEHICLE',
  'CREATE_FEE_TYPE',
  'UPDATE_FEE_TYPE',
  'DEACTIVATE_FEE',
  'CREATE_FEE_RATE',
  'CREATE_EXEMPTION',
  'REVOKE_EXEMPTION',
  'CREATE_BILLING_PERIOD',
  'GENERATE_INVOICES',
  'CLOSE_BILLING_PERIOD',
  'CREATE_UTILITY_READING',
  'UPDATE_UTILITY_READING',
  'CREATE_BACKUP',
];

const AUDIT_ENTITY_OPTIONS = [
  'USER',
  'HOUSEHOLD',
  'RESIDENT',
  'VEHICLE',
  'FEE_TYPE',
  'FEE_RATE',
  'FEE_EXEMPTION',
  'BILLING_PERIOD',
  'UTILITY_READING',
  'SYSTEM',
  'ENDPOINT',
];

export const AuditLogsPage: React.FC = () => {
  const { error: toastError } = useToast();
  const [logs, setAuditLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  // Server-side filters matching GET /api/v1/audit-logs
  const [actionFilter, setActionFilter] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [userIdFilter, setUserIdFilter] = useState('');
  const [debouncedAction, setDebouncedAction] = useState('');
  const [debouncedEntityType, setDebouncedEntityType] = useState('');
  const [debouncedUserId, setDebouncedUserId] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [quickFilter, setQuickFilter] = useState('');

  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const nextAction = actionFilter.trim();
    const nextEntity = entityTypeFilter.trim();
    const nextUserId = userIdFilter.trim();
    if (
      debouncedAction === nextAction &&
      debouncedEntityType === nextEntity &&
      debouncedUserId === nextUserId
    ) {
      return;
    }

    const timer = setTimeout(() => {
      setDebouncedAction(nextAction);
      setDebouncedEntityType(nextEntity);
      setDebouncedUserId(nextUserId);
      setPage(1);
    }, 300);

    return () => clearTimeout(timer);
  }, [
    actionFilter,
    entityTypeFilter,
    userIdFilter,
    debouncedAction,
    debouncedEntityType,
    debouncedUserId,
  ]);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const parsedUserId = debouncedUserId ? Number(debouncedUserId) : undefined;
      const data = await ApiClient.getAuditLogs({
        page,
        page_size: PAGE_SIZE,
        action: debouncedAction || undefined,
        entity_type: debouncedEntityType || undefined,
        user_id: parsedUserId && !isNaN(parsedUserId) ? parsedUserId : undefined,
        from: fromDate || undefined,
        to: toDate || undefined,
      });
      setAuditLogs(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải nhật ký kiểm toán từ máy chủ.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [page, debouncedAction, debouncedEntityType, debouncedUserId, fromDate, toDate, toastError]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const handleResetFilters = () => {
    setActionFilter('');
    setEntityTypeFilter('');
    setUserIdFilter('');
    setDebouncedAction('');
    setDebouncedEntityType('');
    setDebouncedUserId('');
    setFromDate('');
    setToDate('');
    setQuickFilter('');
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const filtered = logs.filter((l) => {
    const q = quickFilter.trim().toLowerCase();
    if (!q) return true;
    return (
      l.action.toLowerCase().includes(q) ||
      l.entity_type.toLowerCase().includes(q) ||
      (l.reason && l.reason.toLowerCase().includes(q)) ||
      (l.ip_address && l.ip_address.includes(q)) ||
      (l.entity_id && l.entity_id.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-blue-600" />
            <span>Nhật ký hoạt động hệ thống</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Lưu vết bất biến các thao tác nghiệp vụ và bảo mật theo thời gian, người dùng, hành động và đối tượng.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={loadLogs}
          isLoading={loading}
          icon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          Làm mới
        </Button>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Không thể tải dữ liệu</p>
              <p className="text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={loadLogs}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Server-side Filters */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">Mã hành động</label>
            <input
              list="audit-actions"
              placeholder="Ví dụ: LOCK_USER, CLOSE_BILLING_PERIOD..."
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
            <datalist id="audit-actions">
              {AUDIT_ACTION_OPTIONS.map((opt) => (
                <option key={opt} value={opt} />
              ))}
            </datalist>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">Loại đối tượng</label>
            <input
              list="audit-entities"
              placeholder="Ví dụ: USER, HOUSEHOLD..."
              value={entityTypeFilter}
              onChange={(e) => setEntityTypeFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
            <datalist id="audit-entities">
              {AUDIT_ENTITY_OPTIONS.map((opt) => (
                <option key={opt} value={opt} />
              ))}
            </datalist>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">Mã người dùng</label>
            <input
              type="number"
              min="1"
              placeholder="ID người thao tác"
              value={userIdFilter}
              onChange={(e) => setUserIdFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">Từ ngày</label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => {
                setFromDate(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1">Đến ngày</label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => {
                setToDate(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-1">
          <div className="flex-1">
            <Input
              placeholder="Lọc nhanh trên trang hiện tại theo lý do, địa chỉ IP, mã đối tượng..."
              value={quickFilter}
              onChange={(e) => setQuickFilter(e.target.value)}
              icon={<Search className="w-4 h-4" />}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetFilters}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Đặt lại bộ lọc
          </Button>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between text-xs">
          <h3 className="text-sm font-bold text-slate-800">Danh sách nhật ký kiểm toán</h3>
          <span className="text-slate-500 font-mono">Tổng cộng: {total} bản ghi</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Người dùng</th>
                <th className="py-3 px-4">Hành động</th>
                <th className="py-3 px-4">Đối tượng</th>
                <th className="py-3 px-4">Lý do / Mô tả</th>
                <th className="py-3 px-4">Địa chỉ IP</th>
                <th className="py-3 px-4 text-right">Chi tiết</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải nhật ký kiểm toán...' : 'Không có bản ghi nhật ký phù hợp.'}
                  </td>
                </tr>
              ) : (
                filtered.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-50">
                    <td className="py-3.5 px-4 font-mono text-slate-600 whitespace-nowrap">
                      {new Date(l.created_at).toLocaleString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {l.user_id ? `#${l.user_id}` : 'Hệ thống'}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-mono font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md">
                        {l.action}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-700 font-mono">
                      {l.entity_type} {l.entity_id ? `(#${l.entity_id})` : ''}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 max-w-xs truncate">{l.reason || '---'}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">{l.ip_address || '---'}</td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedLog(l)}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800 p-1 rounded transition inline-flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Xem</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
          <span>
            Trang {page} / {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Trang trước
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Trang sau
            </Button>
          </div>
        </div>
      </div>

      {/* Modal View JSON Detail */}
      {selectedLog && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedLog(null)}
          title={`Chi tiết nhật ký hoạt động #${selectedLog.id} - ${selectedLog.action}`}
          description={`Thực hiện lúc ${new Date(selectedLog.created_at).toLocaleString('vi-VN')}`}
        >
          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2 p-3 bg-slate-50 rounded-xl text-slate-700">
              <div>
                <span className="text-slate-400">Người thực hiện:</span>{' '}
                {selectedLog.user_id ? `#${selectedLog.user_id}` : 'Hệ thống'}
              </div>
              <div>
                <span className="text-slate-400">Địa chỉ IP:</span> {selectedLog.ip_address || '---'}
              </div>
              <div>
                <span className="text-slate-400">Đối tượng:</span> {selectedLog.entity_type}{' '}
                {selectedLog.entity_id ? `#${selectedLog.entity_id}` : ''}
              </div>
              <div>
                <span className="text-slate-400">Thiết bị:</span>{' '}
                <span className="truncate inline-block max-w-[140px] align-bottom">
                  {selectedLog.user_agent || '---'}
                </span>
              </div>
            </div>

            {selectedLog.reason && (
              <div className="p-3 bg-blue-50/50 border border-blue-100 rounded-xl text-blue-900">
                <span className="font-bold">Lý do:</span> {selectedLog.reason}
              </div>
            )}

            <div>
              <p className="font-bold text-slate-700 mb-1">Dữ liệu trước thay đổi:</p>
              <pre className="bg-slate-900 text-emerald-400 p-3 rounded-xl font-mono text-[11px] overflow-x-auto max-h-40">
                {JSON.stringify(selectedLog.old_value || {}, null, 2)}
              </pre>
            </div>

            <div>
              <p className="font-bold text-slate-700 mb-1">Dữ liệu sau thay đổi:</p>
              <pre className="bg-slate-900 text-blue-400 p-3 rounded-xl font-mono text-[11px] overflow-x-auto max-h-40">
                {JSON.stringify(selectedLog.new_value || {}, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="primary" onClick={() => setSelectedLog(null)}>
                Đóng
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
