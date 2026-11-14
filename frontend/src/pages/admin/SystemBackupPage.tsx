import React, { useEffect, useState } from 'react';
import { Database, HardDriveDownload, Clock, CheckCircle2, AlertCircle, Play } from 'lucide-react';
import { ApiClient } from '../../api';
import { BackupJob } from '../../types';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { useToast } from '../../context/ToastContext';

export const SystemBackupPage: React.FC = () => {
  const { success, error } = useToast();
  const [jobs, setJobs] = useState<BackupJob[]>([]);
  const [backingUp, setBackingUp] = useState(false);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const data = await ApiClient.getBackupJobs();
      setJobs(data);
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleTriggerBackup = async () => {
    setBackingUp(true);
    try {
      await new Promise((r) => setTimeout(r, 1200));
      const job = await ApiClient.triggerBackup();
      success(`Sao lưu CSDL thành công! Tệp tin: ${job.file_path} (US-45).`);
      loadJobs();
    } catch (err: any) {
      error(err.message);
    } finally {
      setBackingUp(false);
    }
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return '---';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Database className="w-6 h-6 text-blue-600" />
            <span>Sao Lưu & Phục Hồi CSDL PostgreSQL (US-45)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Lập lịch tự động sao lưu định kỳ lúc 02:00 sáng hàng ngày, lưu trữ 30 ngày với thời gian phục hồi RTO $\le$ 2 giờ (NFR-002, AC-45.1).
          </p>
        </div>

        <Button
          onClick={handleTriggerBackup}
          variant="primary"
          isLoading={backingUp}
          icon={<HardDriveDownload className="w-4 h-4" />}
        >
          Kích hoạt sao lưu ngay
        </Button>
      </div>

      {/* Backup Schedule Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 text-xs text-blue-900 flex items-start gap-3">
        <Clock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-bold">Lịch trình tự động (System Cronjob):</p>
          <p className="mt-0.5 leading-relaxed text-blue-800">
            Hệ thống tự động thực thi lệnh pg_dump xuất toàn bộ 28 bảng và views lúc <strong>02:00 sáng mỗi ngày</strong>. Các bản sao lưu được nén Gzip và lưu trữ luân phiên trong 30 ngày.
          </p>
        </div>
      </div>

      {/* Backup Jobs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Lịch sử các phiên sao lưu</h3>
          <span className="text-xs text-slate-500">Mã hóa toàn vẹn dữ liệu tài chính</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Thời điểm yêu cầu</th>
                <th className="py-3 px-4">Hình thức / Người yêu cầu</th>
                <th className="py-3 px-4">Thời gian hoàn tất</th>
                <th className="py-3 px-4">Dung lượng file</th>
                <th className="py-3 px-4">Đường dẫn tệp tin sao lưu</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-slate-50">
                  <td className="py-3.5 px-4 font-mono text-slate-800">
                    {new Date(job.requested_at).toLocaleString('vi-VN')}
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-700">
                    {job.requested_by_name || 'Hệ thống tự động (Cronjob)'}
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">
                    {job.finished_at ? new Date(job.finished_at).toLocaleTimeString('vi-VN') : '---'}
                  </td>
                  <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                    {formatBytes(job.size_bytes)}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                    {job.file_path || '---'}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <Badge variant={job.status === 'SUCCEEDED' ? 'success' : 'danger'} dot size="sm">
                      {job.status === 'SUCCEEDED' ? 'Thành công' : 'Thất bại'}
                    </Badge>
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
