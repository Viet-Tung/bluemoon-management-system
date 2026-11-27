import React, { useEffect, useState, useCallback } from 'react';
import { Database, HardDriveDownload, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import { ApiClient } from '../../api';
import { BackupJob } from '../../types';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 20;

export const SystemBackupPage: React.FC = () => {
  const { success, error: toastError } = useToast();
  const [jobs, setJobs] = useState<BackupJob[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [backingUp, setBackingUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await ApiClient.getBackupJobs({ page, page_size: PAGE_SIZE });
      setJobs(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải lịch sử sao lưu từ máy chủ.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [page, toastError]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleTriggerBackup = async () => {
    setBackingUp(true);
    try {
      const job = await ApiClient.triggerBackup();
      success(`Đã khởi tạo tiến trình sao lưu dữ liệu (Bản ghi #${job.id}, trạng thái: ${job.status}).`);
      if (page !== 1) {
        setPage(1);
      } else {
        loadJobs();
      }
    } catch (err: any) {
      toastError(err.message);
    } finally {
      setBackingUp(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return '---';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCEEDED':
        return <Badge variant="success" dot size="sm">Thành công</Badge>;
      case 'RUNNING':
        return <Badge variant="info" dot size="sm">Đang sao lưu</Badge>;
      case 'QUEUED':
        return <Badge variant="warning" dot size="sm">Chờ xử lý</Badge>;
      case 'FAILED':
        return <Badge variant="danger" dot size="sm">Thất bại</Badge>;
      default:
        return <Badge size="sm">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Database className="w-6 h-6 text-blue-600" />
            <span>Sao lưu dữ liệu hệ thống</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Lập lịch tự động sao lưu định kỳ lúc 02:00 sáng hàng ngày để đảm bảo an toàn dữ liệu.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadJobs}
            isLoading={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
          <Button
            onClick={handleTriggerBackup}
            variant="primary"
            size="sm"
            isLoading={backingUp}
            icon={<HardDriveDownload className="w-3.5 h-3.5" />}
          >
            Kích hoạt sao lưu ngay
          </Button>
        </div>
      </div>

      {/* Backend Connection Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Lỗi kết nối máy chủ</p>
              <p className="text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={loadJobs}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Backup Schedule Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 text-xs text-blue-900 flex items-start gap-3">
        <Clock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-bold">Chính sách sao lưu hệ thống:</p>
          <p className="mt-0.5 leading-relaxed text-blue-800">
            Hệ thống hỗ trợ kích hoạt sao lưu dữ liệu toàn vẹn bằng lệnh thủ công hoặc tự động. Các bản sao lưu được lưu trữ an toàn nhằm phục vụ quy trình khôi phục sự cố khẩn cấp.
          </p>
        </div>
      </div>

      {/* Backup Jobs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Lịch sử các phiên sao lưu</h3>
          <span className="text-xs text-slate-500 font-mono">Tổng số: {total} phiên</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Mã phiên</th>
                <th className="py-3 px-4">Thời điểm yêu cầu</th>
                <th className="py-3 px-4">Người yêu cầu</th>
                <th className="py-3 px-4">Thời gian hoàn tất</th>
                <th className="py-3 px-4">Dung lượng file</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải lịch sử sao lưu...' : 'Chưa có bản ghi sao lưu nào.'}
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50">
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-700">#{job.id}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {new Date(job.requested_at).toLocaleString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4 text-slate-700">
                      {job.requested_by ? `Tài khoản #${job.requested_by}` : 'Hệ thống tự động'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">
                      {job.finished_at ? new Date(job.finished_at).toLocaleString('vi-VN') : '---'}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">
                      {formatBytes(job.size_bytes)}
                    </td>
                    <td className="py-3.5 px-4 text-center">{getStatusBadge(job.status)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
          <span>
            Trang {page} / {totalPages} (Tổng {total} phiên sao lưu)
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
    </div>
  );
};
