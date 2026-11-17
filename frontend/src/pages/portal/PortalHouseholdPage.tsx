import React, { useEffect, useState } from 'react';
import {
  Building,
  Users,
  FileEdit,
  Upload,
  Clock,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Send,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { ProfileChangeRequest, Resident } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const PortalHouseholdPage: React.FC = () => {
  const { success, error } = useToast();
  const [residents, setResidents] = useState<Resident[]>([]);
  const [requests, setRequests] = useState<ProfileChangeRequest[]>([]);

  // Request Form Modal (US-34)
  const [modalOpen, setModalOpen] = useState(false);
  const [requestType, setRequestType] = useState<'UPDATE_RESIDENT' | 'ADD_RESIDENT' | 'UPDATE_HOUSEHOLD'>('ADD_RESIDENT');
  const [residentName, setResidentName] = useState('');
  const [dob, setDob] = useState('2026-10-10');
  const [relationship, setRelationship] = useState('Con');
  const [evidenceUrl, setEvidenceUrl] = useState('https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=500');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const r = await ApiClient.getResidents();
      setResidents(r.filter((item) => item.household_id === 1));
      const reqs = await ApiClient.getChangeRequests();
      setRequests(reqs.filter((item) => item.household_id === 1));
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleSubmitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!residentName) return;

    try {
      await ApiClient.submitChangeRequest({
        request_type: requestType,
        proposed_data: {
          full_name: residentName,
          date_of_birth: dob,
          relationship_to_head: relationship,
        },
        evidence_files: [evidenceUrl],
      });

      success('Yêu cầu chỉnh sửa thông tin đã được gửi tới Ban Quản Trị xét duyệt (US-34).');
      setModalOpen(false);
      setResidentName('');
      loadData();
    } catch (err: any) {
      error(err.message);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md">
            Cổng Cư Dân Trực Tuyến
          </span>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
            <Building className="w-6 h-6 text-blue-600" />
            <span>Hồ Sơ Hộ Gia Đình Căn B1204 (US-33, US-34)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Tra cứu thông tin căn hộ, nhân khẩu trong hộ và gửi đề nghị chỉnh sửa có đính kèm ảnh minh chứng trực tuyến.
          </p>
        </div>

        <Button
          onClick={() => setModalOpen(true)}
          variant="primary"
          icon={<FileEdit className="w-4 h-4" />}
        >
          Gửi đề nghị sửa đổi thông tin
        </Button>
      </div>

      {/* Apartment Overview Card */}
      <div className="bg-gradient-to-tr from-blue-900 to-indigo-800 rounded-3xl p-6 text-white shadow-lg grid grid-cols-2 sm:grid-cols-4 gap-6">
        <div>
          <p className="text-xs text-blue-200 uppercase font-semibold">Mã Căn Hộ</p>
          <p className="text-2xl font-bold font-mono mt-1">B1204</p>
          <p className="text-[11px] text-blue-200 mt-0.5">Tầng 12 • Tháp B</p>
        </div>
        <div>
          <p className="text-xs text-blue-200 uppercase font-semibold">Diện Tích Thông Thủy</p>
          <p className="text-2xl font-bold font-mono mt-1">85.5 m²</p>
          <p className="text-[11px] text-blue-200 mt-0.5">Căn góc view hồ</p>
        </div>
        <div>
          <p className="text-xs text-blue-200 uppercase font-semibold">Chủ Hộ Đại Diện</p>
          <p className="text-xl font-bold mt-1">Phạm Minh Tuấn</p>
          <p className="text-[11px] text-blue-200 mt-0.5">SĐT: 0934.567.890</p>
        </div>
        <div>
          <p className="text-xs text-blue-200 uppercase font-semibold">Số Dư Có (Credit)</p>
          <p className="text-2xl font-bold font-mono text-emerald-300 mt-1">50.000 đ</p>
          <p className="text-[11px] text-blue-200 mt-0.5">Đã cấn trừ kỳ tháng 11</p>
        </div>
      </div>

      {/* Residents in household */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-800">Danh sách nhân khẩu đang cư trú ({residents.length} người)</h3>
          </div>
          <span className="text-xs text-slate-500">Bảo mật IDOR: Chỉ hiển thị dữ liệu thành viên của căn B1204 (AC-44.2)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Họ và Tên</th>
                <th className="py-3 px-4">Ngày sinh</th>
                <th className="py-3 px-4">Giới tính</th>
                <th className="py-3 px-4">Số CCCD</th>
                <th className="py-3 px-4">Quan hệ với chủ hộ</th>
                <th className="py-3 px-4 text-center">Tình trạng</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {residents.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50">
                  <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                    <span>{r.full_name}</span>
                    {r.is_head && (
                      <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-1.5 py-0.5 rounded">
                        Chủ hộ
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-600">
                    {new Date(r.date_of_birth).toLocaleDateString('vi-VN')}
                  </td>
                  <td className="py-3 px-4 text-slate-700">
                    {r.gender === 'NAM' ? 'Nam' : 'Nữ'}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-800">
                    {r.cccd || <span className="text-slate-400 italic">Dưới 14 tuổi</span>}
                  </td>
                  <td className="py-3 px-4 text-slate-700 font-medium">{r.relationship_to_head}</td>
                  <td className="py-3 px-4 text-center">
                    <Badge variant="thuong_tru" dot size="sm">
                      Thường trú
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* History of Change Requests (US-34) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-800">Lịch sử Đề nghị chỉnh sửa thông tin gửi BQT (US-34)</h3>
          </div>
        </div>

        {requests.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            Chưa có đề nghị chỉnh sửa nào được gửi
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {requests.map((req) => (
              <div key={req.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800">
                      {req.request_type === 'ADD_RESIDENT'
                        ? 'Thêm nhân khẩu mới'
                        : req.request_type === 'UPDATE_RESIDENT'
                        ? 'Cập nhật thông tin nhân khẩu'
                        : 'Sửa thông tin hộ'}
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
                        : 'Đang chờ BQT duyệt'}
                    </Badge>
                  </div>
                  <p className="text-slate-600 mt-1">
                    Nội dung: <strong>{req.proposed_data.full_name}</strong> ({req.proposed_data.relationship_to_head} - Sinh năm {req.proposed_data.date_of_birth})
                  </p>
                  {req.reject_reason && (
                    <p className="text-rose-600 font-semibold mt-1 bg-rose-50 p-2 rounded-lg border border-rose-200">
                      Lý do BQT từ chối: {req.reject_reason}
                    </p>
                  )}
                  <p className="text-[11px] text-slate-400 mt-1">
                    Gửi lúc: {new Date(req.created_at).toLocaleString('vi-VN')}
                  </p>
                </div>

                {req.evidence_files && req.evidence_files.length > 0 && (
                  <div className="flex-shrink-0">
                    <img
                      src={req.evidence_files[0]}
                      alt="Giấy tờ minh chứng"
                      className="w-16 h-16 object-cover rounded-xl border border-slate-200 shadow-2xs"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Submit Change Request (US-34) */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Gửi đề nghị chỉnh sửa nhân khẩu (US-34)"
        description="Đề nghị của bạn sẽ được chuyển đến Trưởng Ban Quản Trị xem xét và phê duyệt trực tuyến."
      >
        <form onSubmit={handleSubmitRequest} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Loại yêu cầu</label>
            <select
              value={requestType}
              onChange={(e) => setRequestType(e.target.value as any)}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="ADD_RESIDENT">Đăng ký thêm thành viên mới trong gia đình</option>
              <option value="UPDATE_RESIDENT">Đính chính thông tin cá nhân / CCCD</option>
              <option value="UPDATE_HOUSEHOLD">Cập nhật số điện thoại / Email liên hệ của hộ</option>
            </select>
          </div>

          <Input
            label="Họ và tên thành viên"
            placeholder="Ví dụ: Phạm Minh Châu..."
            value={residentName}
            onChange={(e) => setResidentName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Ngày sinh"
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              required
            />
            <Input
              label="Quan hệ với chủ hộ"
              placeholder="Con, Vợ, Bố mẹ..."
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Ảnh giấy tờ minh chứng (Giấy khai sinh / CCCD)
            </label>
            <div className="flex items-center gap-3">
              <Input
                value={evidenceUrl}
                onChange={(e) => setEvidenceUrl(e.target.value)}
                placeholder="URL ảnh hoặc file đính kèm..."
              />
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Đính kèm bản chụp rõ nét giấy tờ để Ban Quản Trị đối chiếu xét duyệt (AC-34.1).
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setModalOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit" icon={<Send className="w-4 h-4" />}>
              Gửi yêu cầu xét duyệt
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
