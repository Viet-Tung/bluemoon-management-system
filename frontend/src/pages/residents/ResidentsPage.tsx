import React, { useEffect, useState } from 'react';
import {
  Users,
  Plus,
  Search,
  UserPlus,
  ShieldAlert,
  Calendar,
  Check,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { Resident } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const ResidentsPage: React.FC = () => {
  const { success, error } = useToast();
  const [residents, setResidents] = useState<Resident[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Modal Add Resident
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [fullName, setFullName] = useState('');
  const [dob, setDob] = useState('1995-01-01');
  const [gender, setGender] = useState<'NAM' | 'NU' | 'KHAC'>('NAM');
  const [cccd, setCccd] = useState('');
  const [phone, setPhone] = useState('');
  const [relationship, setRelationship] = useState('Thành viên');
  const [isHead, setIsHead] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await ApiClient.getResidents();
      setResidents(data);
    } catch (err: any) {
      error(err.message || 'Không thể tải danh sách nhân khẩu');
    }
  };

  const calculateAge = (dobString: string) => {
    const birthYear = new Date(dobString).getFullYear();
    return new Date().getFullYear() - birthYear;
  };

  const handleAddResident = async (e: React.FormEvent) => {
    e.preventDefault();

    const age = calculateAge(dob);
    // AC-05.3: Trẻ em dưới 14 tuổi cho phép để trống CCCD
    if (age >= 14 && !cccd) {
      error('Nhân khẩu từ 14 tuổi trở lên bắt buộc phải nhập số CCCD (AC-05.3).');
      return;
    }

    try {
      await ApiClient.addResident({
        full_name: fullName,
        date_of_birth: dob,
        gender,
        cccd: cccd || undefined,
        phone,
        relationship_to_head: relationship,
        is_head: isHead,
      });

      success(`Đã thêm nhân khẩu ${fullName} vào sổ hộ thành công!`);
      setAddModalOpen(false);
      setFullName('');
      setCccd('');
      setPhone('');
      loadData();
    } catch (err: any) {
      error(err.message);
    }
  };

  const filtered = residents.filter((r) => {
    const matchSearch =
      r.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.cccd && r.cccd.includes(searchTerm)) ||
      (r.phone && r.phone.includes(searchTerm));
    const matchStatus = statusFilter === 'ALL' || r.residence_status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-600" />
            <span>Quản lý Nhân khẩu & Cư trú (US-05..US-10)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Theo dõi thường trú, tạm trú, tạm vắng và biến động nhân khẩu theo quy chuẩn Công an khu vực (DOC-03).
          </p>
        </div>

        <Button
          onClick={() => setAddModalOpen(true)}
          variant="primary"
          icon={<UserPlus className="w-4 h-4" />}
        >
          Thêm nhân khẩu mới
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-center gap-3">
        <div className="flex-1 w-full">
          <Input
            placeholder="Tìm theo họ tên, số CCCD hoặc số điện thoại..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            icon={<Search className="w-4 h-4" />}
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">Trạng thái:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full sm:w-44 bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả tình trạng</option>
            <option value="THUONG_TRU">Thường trú</option>
            <option value="TAM_VANG">Tạm vắng</option>
            <option value="DA_CHUYEN_DI">Đã chuyển đi</option>
          </select>
        </div>
      </div>

      {/* Residents Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3.5 px-4">Họ và Tên</th>
                <th className="py-3.5 px-4">Ngày sinh / Tuổi</th>
                <th className="py-3.5 px-4">Giới tính</th>
                <th className="py-3.5 px-4">Số CCCD / Định danh</th>
                <th className="py-3.5 px-4">Số điện thoại</th>
                <th className="py-3.5 px-4">Quan hệ với chủ hộ</th>
                <th className="py-3.5 px-4 text-center">Trạng thái cư trú</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((r) => {
                const age = calculateAge(r.date_of_birth);
                return (
                  <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 flex items-center gap-2">
                      <span>{r.full_name}</span>
                      {r.is_head && (
                        <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-1.5 py-0.5 rounded-md">
                          Chủ hộ
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      {new Date(r.date_of_birth).toLocaleDateString('vi-VN')} ({age} tuổi)
                    </td>
                    <td className="py-3.5 px-4 text-slate-700">
                      {r.gender === 'NAM' ? 'Nam' : r.gender === 'NU' ? 'Nữ' : 'Khác'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-800">
                      {r.cccd ? (
                        r.cccd
                      ) : (
                        <span className="text-amber-600 italic">Trẻ em &lt; 14t (AC-05.3)</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">{r.phone || '---'}</td>
                    <td className="py-3.5 px-4 text-slate-700 font-medium">{r.relationship_to_head}</td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge
                        variant={
                          r.residence_status === 'THUONG_TRU'
                            ? 'thuong_tru'
                            : r.residence_status === 'TAM_VANG'
                            ? 'tam_vang'
                            : 'neutral'
                        }
                        dot
                      >
                        {r.residence_status === 'THUONG_TRU'
                          ? 'Thường trú'
                          : r.residence_status === 'TAM_VANG'
                          ? 'Tạm vắng'
                          : 'Đã chuyển đi'}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Add Resident */}
      <Modal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title="Thêm nhân khẩu vào hộ gia đình (US-05)"
        description="Đăng ký thêm thành viên vào sổ hộ khẩu BlueMoon."
      >
        <form onSubmit={handleAddResident} className="space-y-4">
          <Input
            label="Họ và tên nhân khẩu"
            placeholder="Ví dụ: Nguyễn Văn An..."
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Ngày tháng năm sinh"
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              required
            />
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Giới tính</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value as any)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="NAM">Nam</option>
                <option value="NU">Nữ</option>
                <option value="KHAC">Khác</option>
              </select>
            </div>
          </div>

          <Input
            label="Số CCCD / Định danh cá nhân"
            placeholder="12 chữ số (để trống nếu dưới 14 tuổi)"
            value={cccd}
            onChange={(e) => setCccd(e.target.value)}
            helperText="Quy tắc AC-05.3: Trẻ em dưới 14 tuổi được miễn nhập CCCD."
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Số điện thoại"
              placeholder="09..."
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <Input
              label="Quan hệ với chủ hộ"
              placeholder="Vợ, Con, Bố mẹ..."
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              required
            />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="isHeadCheck"
              checked={isHead}
              onChange={(e) => setIsHead(e.target.checked)}
              className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="isHeadCheck" className="text-xs font-semibold text-slate-700">
              Đặt làm Chủ hộ đại diện (AC-05.1: mỗi hộ chỉ có 1 chủ hộ đang hoạt động)
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddModalOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Xác nhận thêm
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
