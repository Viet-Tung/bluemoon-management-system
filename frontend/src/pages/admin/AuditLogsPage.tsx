import React, { useEffect, useState } from 'react';
import { ShieldCheck, Search, Eye, Clock, Terminal } from 'lucide-react';
import { ApiClient } from '../../api';
import { AuditLog } from '../../types';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const AuditLogsPage: React.FC = () => {
  const { error } = useToast();
  const [logs, setAuditLogs] = useState<AuditLog[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    try {
      const data = await ApiClient.getAuditLogs();
      setAuditLogs(data);
    } catch (err: any) {
      error(err.message);
    }
  };

  const filtered = logs.filter(
    (l) =>
      l.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.username && l.username.toLowerCase().includes(searchTerm.toLowerCase())) ||
      l.entity_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-blue-600" />
          <span>Nhật Ký Thao Tác Kiểm Toán Bất Biến (US-32)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Lưu vết minh bạch 100% các hành vi nhạy cảm: thay đổi đơn giá, hủy biên lai, chuyển nhượng căn hộ, cấp quyền (Database Trigger chặn UPDATE/DELETE/TRUNCATE).
        </p>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs">
        <Input
          placeholder="Tìm theo hành động (VD: LOGIN, COLLECT_PAYMENT), người thực hiện..."
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
                <th className="py-3 px-4">Người thực hiện</th>
                <th className="py-3 px-4">Hành động (Action)</th>
                <th className="py-3 px-4">Thực thể (Entity)</th>
                <th className="py-3 px-4">Lý do / Mô tả</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4 text-right">Chi tiết</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((l) => (
                <tr key={l.id} className="hover:bg-slate-50">
                  <td className="py-3.5 px-4 font-mono text-slate-600">
                    {new Date(l.created_at).toLocaleString('vi-VN')}
                  </td>
                  <td className="py-3.5 px-4 font-bold text-slate-800">{l.username || 'System'}</td>
                  <td className="py-3.5 px-4">
                    <span className="font-mono font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md">
                      {l.action}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-700 font-mono">
                    {l.entity_type} {l.entity_id ? `(#${l.entity_id})` : ''}
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">{l.reason || '---'}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-400">{l.ip_address || '127.0.0.1'}</td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => setSelectedLog(l)}
                      className="text-xs font-semibold text-blue-600 hover:text-blue-800 p-1 rounded transition"
                    >
                      Xem JSON
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal View JSON Diff */}
      {selectedLog && (
        <Modal
          isOpen={!!selectedLog}
          onClose={() => setSelectedLog(null)}
          title={`Chi tiết Audit Log #${selectedLog.id} - ${selectedLog.action}`}
          size="lg"
        >
          <div className="space-y-4 text-xs">
            <div className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono overflow-x-auto space-y-2">
              <p className="text-emerald-400 font-bold">// Dữ liệu ghi nhận kiểm toán bất biến</p>
              <pre className="text-[11px] leading-relaxed">
                {JSON.stringify(selectedLog, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
