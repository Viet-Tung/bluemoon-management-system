import React, { useState, useRef } from 'react';
import { Upload, FileSpreadsheet, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { ApiClient, ApiError } from '../../api';
import { ApiErrorDetail, ImportResult } from '../../types';
import { Modal } from './Modal';
import { Button } from './Button';
import { useToast } from '../../context/ToastContext';

interface ExcelImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export const ExcelImportModal: React.FC<ExcelImportModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success, error: toastError } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [errorSummary, setErrorSummary] = useState<string | null>(null);
  const [rowErrors, setRowErrors] = useState<ApiErrorDetail[]>([]);

  const resetState = () => {
    setSelectedFile(null);
    setResult(null);
    setErrorSummary(null);
    setRowErrors([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const validateAndSetFile = (file: File | undefined) => {
    setResult(null);
    setErrorSummary(null);
    setRowErrors([]);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      setErrorSummary('Chỉ hỗ trợ định dạng tệp Excel (.xlsx).');
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErrorSummary('Kích thước tệp vượt quá giới hạn cho phép (tối đa 10 MB).');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      toastError('Vui lòng chọn tệp Excel (.xlsx) trước khi tải lên.');
      return;
    }

    setUploading(true);
    setResult(null);
    setErrorSummary(null);
    setRowErrors([]);

    try {
      const res = await ApiClient.importExcel(selectedFile);
      setResult(res);
      success(`Nhập dữ liệu thành công: ${res.imported_rows}/${res.total_rows} dòng.`);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorSummary(err.message);
        setRowErrors(err.details || []);
      } else {
        setErrorSummary(err.message || 'Không thể nhập dữ liệu từ tệp Excel.');
      }
      toastError(err.message || 'Nhập dữ liệu Excel thất bại.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      size="lg"
      title="Nhập dữ liệu Căn hộ, Hộ gia đình & Nhân khẩu từ Excel"
      description="Tải lên tệp .xlsx để nhập hàng loạt. Dữ liệu chỉ được lưu khi toàn bộ các dòng đều hợp lệ."
    >
      <form onSubmit={handleUpload} className="space-y-4 text-xs">
        {/* Expected format guide */}
        <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-2xl text-blue-900 space-y-2">
          <div className="flex items-center gap-2 font-bold">
            <FileSpreadsheet className="w-4 h-4 text-blue-600" />
            <span>Cấu trúc cột tiêu đề (Dòng 1 của Sheet đầu tiên)</span>
          </div>
          <p className="text-blue-800 leading-relaxed">
            <span className="font-semibold">Các cột bắt buộc:</span>{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Mã căn hộ</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Tầng</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Diện tích</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Mã hộ gia đình</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Họ và tên</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Ngày sinh</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Giới tính</code>
          </p>
          <p className="text-blue-800 leading-relaxed">
            <span className="font-semibold">Các cột tùy chọn:</span>{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">SĐT liên hệ</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Email liên hệ</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Số CCCD</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Quan hệ với chủ hộ</code>,{' '}
            <code className="bg-white/80 px-1.5 py-0.5 rounded font-mono text-[11px]">Là chủ hộ</code>
          </p>
          <p className="text-[11px] text-blue-700">
            * Ngày sinh hỗ trợ định dạng YYYY-MM-DD hoặc DD/MM/YYYY. Giới tính: Nam / Nữ / Khác. Công dân từ 14 tuổi trở lên bắt buộc có CCCD/CMND (9–12 chữ số).
          </p>
        </div>

        {/* File Picker */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 hover:border-blue-500 hover:bg-blue-50/30 rounded-2xl p-6 text-center cursor-pointer transition"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(e) => validateAndSetFile(e.target.files?.[0])}
          />
          <Upload className="w-8 h-8 text-blue-600 mx-auto mb-2" />
          {selectedFile ? (
            <div className="space-y-1">
              <p className="font-bold text-slate-900">{selectedFile.name}</p>
              <p className="text-[11px] text-slate-500">
                Dung lượng: {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
              <button
                type="button"
                onClick={(ev) => {
                  ev.stopPropagation();
                  resetState();
                }}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600 hover:underline mt-1"
              >
                <X className="w-3 h-3" />
                <span>Chọn tệp khác</span>
              </button>
            </div>
          ) : (
            <div>
              <p className="font-semibold text-slate-700">
                Nhấn để chọn tệp Excel (.xlsx) từ máy tính
              </p>
              <p className="text-[11px] text-slate-400 mt-1">Dung lượng tối đa 10 MB</p>
            </div>
          )}
        </div>

        {/* Success Result */}
        {result && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-emerald-900 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Nhập dữ liệu hoàn tất!</p>
              <p className="mt-0.5 text-emerald-800">
                Đã xử lý thành công{' '}
                <span className="font-bold font-mono">{result.imported_rows}</span> /{' '}
                <span className="font-mono">{result.total_rows}</span> dòng dữ liệu từ tệp Excel.
              </p>
            </div>
          </div>
        )}

        {/* Validation Errors (422 IMPORT_FAILED) */}
        {errorSummary && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-900 space-y-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Dữ liệu chưa hợp lệ — Chưa có bản ghi nào được lưu</p>
                <p className="text-rose-700 mt-0.5">{errorSummary}</p>
              </div>
            </div>

            {rowErrors.length > 0 && (
              <div className="bg-white rounded-xl border border-rose-200 overflow-hidden max-h-56 overflow-y-auto">
                <table className="w-full text-[11px] text-left">
                  <thead className="bg-rose-100/70 text-rose-900 font-bold sticky top-0">
                    <tr>
                      <th className="py-2 px-3">Dòng</th>
                      <th className="py-2 px-3">Trường dữ liệu</th>
                      <th className="py-2 px-3">Chi tiết lỗi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rose-100">
                    {rowErrors.map((errItem, idx) => (
                      <tr key={idx}>
                        <td className="py-2 px-3 font-mono font-bold text-rose-700">
                          {errItem.row ?? '---'}
                        </td>
                        <td className="py-2 px-3 font-mono text-slate-700">
                          {errItem.field || '---'}
                        </td>
                        <td className="py-2 px-3 text-rose-800">{errItem.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
          <Button variant="outline" type="button" onClick={handleClose}>
            Đóng
          </Button>
          <Button
            variant="primary"
            type="submit"
            isLoading={uploading}
            disabled={!selectedFile || uploading}
            icon={<Upload className="w-3.5 h-3.5" />}
          >
            Tải lên & Nhập dữ liệu
          </Button>
        </div>
      </form>
    </Modal>
  );
};
