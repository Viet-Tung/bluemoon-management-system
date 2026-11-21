import React, { useEffect, useState, useCallback } from 'react';
import { ShieldCheck, Search, Eye, RefreshCw, AlertCircle } from 'lucide-react';
import { ApiClient } from '../../api';
import { AuditLog } from '../../types';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const AuditLogsPage: React.FC = () => {
  const { error: toastError } = useToast();
  const [logs, setAuditLogs] = useState<AuditLog[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await ApiClient.getAuditLogs({ page: 1, page_size: 100 });
      setAuditLogs(data.items || []);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải nhật ký kiểm toán từ máy chủ Backend.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [toastError]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const filtered = logs.filter(
    (l) =>
      l.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.entity_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.reason && l.reason.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (l.ip_address && l.ip_address.includes(searchTerm))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-blue-600" />
            <span>Nhật Ký Thao Tác Kiểm Toán Bất Biến (Sprint 1: US-32)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Lưu vết minh bạch các hành vi nhạy cảm: thay đổi vai trò, khóa tài khoản, tạo hộ gia đình, chuyển nhượng căn hộ.
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
          <Button size="sm" variant="outline" onClick={loadLogs}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Search Bar */}
      <div className="bg-white p-3 rounded-2xl border border-slate-200 shadow-xs">
        <Input
          placeholder="Tìm theo hành động (VD: CHANGE_ROLE, LOCK_USER), thực thể, lý do, IP..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          icon={<Search className="w-4 h-4" />}
        />
      </div>

      {/* Audit Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Hành động (Action)</th>
                <th className="py-3 px-4">Thực thể (Entity)</th>
                <th className="py-3 px-4">Lý do / Mô tả</th>
                <th className="py-3 px-4">Địa chỉ IP</th>
                <th className="py-3 px-4 text-right">Chi tiết</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải nhật ký kiểm toán...' : 'Chưa có bản ghi nhật ký nào.'}
                  </td>
                </tr>
              ) : (
                filtered.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-50">
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {new Date(l.created_at).toLocaleString('vi-VN')}
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
      </div>

      {/* Modal View JSON Detail */}
      {selectedLog && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedLog(null)}
          title={`Chi tiết Audit Log #${selectedLog.id} - ${selectedLog.action}`}
          description={`Thực hiện lúc ${new Date(selectedLog.created_at).toLocaleString('vi-VN')}`}
        >
          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2 p-3 bg-slate-50 rounded-xl text-slate-700">
              <div>
                <span className="text-slate-400">User ID:</span> {selectedLog.user_id || 'System'}
              </div>
              <div>
                <span className="text-slate-400">IP:</span> {selectedLog.ip_address || '---'}
              </div>
              <div>
                <span className="text-slate-400">Entity:</span> {selectedLog.entity_type} #{selectedLog.entity_id}
              </div>
              <div>
                <span className="text-slate-400">User-Agent:</span>{' '}
                <span className="truncate inline-block max-w-[120px] align-bottom">
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
              <p className="font-bold text-slate-700 mb-1">Dữ liệu trước thay đổi (Old Value):</p>
              <pre className="bg-slate-900 text-emerald-400 p-3 rounded-xl font-mono text-[11px] overflow-x-auto max-h-40">
                {JSON.stringify(selectedLog.old_value || {}, null, 2)}
              </pre>
            </div>

            <div>
              <p className="font-bold text-slate-700 mb-1">Dữ liệu sau thay đổi (New Value):</p>
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
