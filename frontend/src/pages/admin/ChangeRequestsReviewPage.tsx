import React, { useEffect, useState } from 'react';
import {
  UserCheck,
  Check,
  X,
  Clock,
  Eye,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { ProfileChangeRequest } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const ChangeRequestsReviewPage: React.FC = () => {
  const { success, error } = useToast();
  const [requests, setRequests] = useState<ProfileChangeRequest[]>([]);
  const [selectedReq, setSelectedReq] = useState<ProfileChangeRequest | null>(null);

  // Reject Modal with mandatory reason (AC-34.3)
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  // Image Preview Modal
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await ApiClient.getChangeRequests();
      setRequests(data);
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleApprove = async (req: ProfileChangeRequest) => {
    try {
      await ApiClient.reviewChangeRequest(req.id, 'APPROVED');
      success(
        `Đã phê duyệt yêu cầu từ căn ${req.apartment_code}. Dữ liệu nhân khẩu đã tự động cập nhật vào CSDL (AC-34.2).`
      );
      loadData();
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReq) return;
    if (!rejectReason.trim()) {
      error('Bắt buộc phải nhập lý do từ chối (AC-34.3).');
      return;
    }

    try {
      await ApiClient.reviewChangeRequest(selectedReq.id, 'REJECTED', rejectReason);
      success(`Đã từ chối yêu cầu từ căn ${selectedReq.apartment_code} với lý do cụ thể.`);
      setRejectModalOpen(false);
      setRejectReason('');
      setSelectedReq(null);
      loadData();
    } catch (err: any) {
      error(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <UserCheck className="w-6 h-6 text-blue-600" />
          <span>Xét duyệt Đề nghị Chỉnh sửa Nhân khẩu Cư dân (US-34)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Ban Quản Trị thẩm định các yêu cầu thêm mới, sửa đổi thông tin nhân khẩu có đối chiếu giấy tờ minh chứng.
        </p>
      </div>

      {/* Requests List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh sách yêu cầu tiếp nhận</h3>
          <span className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-semibold">
            {requests.filter((r) => r.status === 'PENDING').length} yêu cầu đang chờ duyệt
          </span>
        </div>

        <div className="divide-y divide-slate-100">
          {requests.map((req) => (
            <div key={req.id} className="p-6 flex flex-col lg:flex-row items-start justify-between gap-6 text-xs">
              <div className="space-y-3 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sm text-blue-700">
                    Căn {req.apartment_code} ({req.household_code})
                  </span>
                  <Badge
                    size="sm"
                    variant={
                      req.status === 'APPROVED'
                        ? 'success'
                        : req.status === 'REJECTED'
                        ? 'danger'
                        : 'warning'
                    }
                    dot
                  >
                    {req.status === 'APPROVED'
                      ? 'Đã duyệt'
                      : req.status === 'REJECTED'
                      ? 'Đã từ chối'
                      : 'Chờ BQT duyệt'}
                  </Badge>
                </div>

                <div className="bg-slate-50 p-4 rounded-xl space-y-1.5 border border-slate-200">
                  <p className="font-semibold text-slate-800">
                    Loại đề nghị:{' '}
                    {req.request_type === 'ADD_RESIDENT'
                      ? 'Thêm nhân khẩu mới'
                      : req.request_type === 'UPDATE_RESIDENT'
                      ? 'Sửa thông tin nhân khẩu'
                      : 'Đổi thông tin hộ'}
                  </p>
                  <p>Họ tên: <strong className="text-slate-900">{req.proposed_data.full_name}</strong></p>
                  <p>Ngày sinh: {req.proposed_data.date_of_birth} • Quan hệ: {req.proposed_data.relationship_to_head}</p>
                </div>

                {req.reject_reason && (
                  <p className="bg-rose-50 text-rose-800 p-3 rounded-xl border border-rose-200">
                    <strong>Lý do từ chối:</strong> {req.reject_reason} (Người duyệt: {req.reviewed_by_name})
                  </p>
                )}

                <p className="text-[11px] text-slate-400">
                  Người gửi: {req.requested_by_username} • Gửi lúc: {new Date(req.created_at).toLocaleString('vi-VN')}
                </p>
              </div>

              {/* Evidence photo & Actions */}
              <div className="flex flex-col sm:flex-row items-center gap-4 flex-shrink-0">
                {req.evidence_files && req.evidence_files.length > 0 && (
                  <div
                    onClick={() => setPreviewImage(req.evidence_files[0])}
                    className="cursor-pointer group relative"
                  >
                    <img
                      src={req.evidence_files[0]}
                      alt="Giấy tờ minh chứng"
                      className="w-24 h-24 object-cover rounded-xl border border-slate-200 shadow-xs group-hover:opacity-90 transition"
                    />
                    <div className="absolute inset-0 bg-slate-900/30 rounded-xl opacity-0 group-hover:opacity-100 flex items-center justify-center text-white transition">
                      <Eye className="w-5 h-5" />
                    </div>
                  </div>
                )}

                {req.status === 'PENDING' && (
                  <div className="flex flex-col gap-2 w-full sm:w-auto">
                    <Button
                      size="sm"
                      variant="success"
                      onClick={() => handleApprove(req)}
                      icon={<Check className="w-4 h-4" />}
                    >
                      Duyệt yêu cầu
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => {
                        setSelectedReq(req);
                        setRejectModalOpen(true);
                      }}
                      icon={<X className="w-4 h-4" />}
                    >
                      Từ chối
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal Reject with mandatory reason (AC-34.3) */}
      {selectedReq && (
        <Modal
          isOpen={rejectModalOpen}
          onClose={() => setRejectModalOpen(false)}
          title={`Từ chối yêu cầu từ Căn ${selectedReq.apartment_code} (AC-34.3)`}
          description="Bắt buộc phải nhập lý do từ chối để thông báo minh bạch cho cư dân trên Cổng Portal."
        >
          <form onSubmit={handleReject} className="space-y-4">
            <Input
              label="Lý do từ chối (Bắt buộc theo AC-34.3)"
              placeholder="Ví dụ: Giấy khai sinh bị mờ không rõ số, thông tin CCCD không khớp..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              required
            />
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button variant="outline" type="button" onClick={() => setRejectModalOpen(false)}>
                Hủy
              </Button>
              <Button variant="danger" type="submit">
                Xác nhận từ chối
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal Image Zoom */}
      {previewImage && (
        <Modal
          isOpen={!!previewImage}
          onClose={() => setPreviewImage(null)}
          title="Minh chứng giấy tờ do cư dân tải lên"
          size="lg"
        >
          <img src={previewImage} alt="Giấy tờ" className="w-full max-h-[70vh] object-contain rounded-xl" />
        </Modal>
      )}
    </div>
  );
};
