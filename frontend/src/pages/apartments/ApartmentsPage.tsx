import React, { useEffect, useState, useCallback } from 'react';
import {
  Building2,
  Plus,
  Search,
  Home,
  RefreshCw,
  AlertCircle,
  Users,
  ArrowRightLeft,
  UserCheck,
  Ban,
  ShieldCheck,
  CheckCircle,
} from 'lucide-react';
import { ApiClient, ApiError } from '../../api';
import { Apartment, Household, HouseholdCreated } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const ApartmentsPage: React.FC = () => {
  const { success, error: toastError } = useToast();

  const [activeTab, setActiveTab] = useState<'apartments' | 'households'>('apartments');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Apartments State
  const [apartments, setApartments] = useState<Apartment[]>([]);
  const [aptSearch, setAptSearch] = useState('');
  const [aptFloorFilter, setAptFloorFilter] = useState<string>('ALL');
  const [aptStatusFilter, setAptStatusFilter] = useState<string>('ALL');

  // Add Apartment Modal
  const [addAptOpen, setAddAptOpen] = useState(false);
  const [aptCode, setAptCode] = useState('');
  const [aptFloor, setAptFloor] = useState(1);
  const [aptArea, setAptArea] = useState(70);
  const [aptNote, setAptNote] = useState('');

  // Edit Apartment Modal
  const [editAptOpen, setEditAptOpen] = useState(false);
  const [selectedApt, setSelectedApt] = useState<Apartment | null>(null);
  const [editFloor, setEditFloor] = useState(1);
  const [editArea, setEditArea] = useState(70);
  const [editStatus, setEditStatus] = useState<'ACTIVE' | 'INACTIVE'>('ACTIVE');
  const [editNote, setEditNote] = useState('');

  // Households State
  const [households, setHouseholds] = useState<Household[]>([]);
  const [hhSearch, setHhSearch] = useState('');
  const [hhStatusFilter, setHhStatusFilter] = useState<string>('ALL');

  // Add Household Modal
  const [addHhOpen, setAddHhOpen] = useState(false);
  const [hhCode, setHhCode] = useState('');
  const [hhApartmentId, setHhApartmentId] = useState<number | ''>('');
  const [hhPhone, setHhPhone] = useState('');
  const [hhEmail, setHhEmail] = useState('');
  const [hhNote, setHhNote] = useState('');
  // Head details
  const [headName, setHeadName] = useState('');
  const [headDob, setHeadDob] = useState('1990-01-01');
  const [headGender, setHeadGender] = useState('NAM');
  const [headCccd, setHeadCccd] = useState('');
  const [headPhone, setHeadPhone] = useState('');
  const [headEmail, setHeadEmail] = useState('');

  // Created Household Result Modal (showing auto-generated resident account)
  const [createdHhResult, setCreatedHhResult] = useState<HouseholdCreated | null>(null);

  // Deactivate Household Modal
  const [deactivateOpen, setDeactivateOpen] = useState(false);
  const [targetHh, setTargetHh] = useState<Household | null>(null);
  const [deactivateReason, setDeactivateReason] = useState('');

  // Transfer Apartment Modal
  const [transferOpen, setTransferOpen] = useState(false);
  const [transferSourceHh, setTransferSourceHh] = useState<Household | null>(null);
  const [transferTargetHhId, setTransferTargetHhId] = useState<number | ''>('');
  const [transferDate, setTransferDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [transferReason, setTransferReason] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [aptRes, hhRes] = await Promise.all([
        ApiClient.getApartments({ page: 1, page_size: 100 }),
        ApiClient.getHouseholds({ page: 1, page_size: 100 }),
      ]);
      setApartments(aptRes.items || []);
      setHouseholds(hhRes.items || []);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải dữ liệu từ máy chủ Backend.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [toastError]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Add Apartment
  const handleAddApartment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await ApiClient.createApartment({
        code: aptCode.trim(),
        floor: Number(aptFloor),
        area_m2: Number(aptArea),
        note: aptNote.trim() || undefined,
      });
      success(`Đã thêm căn hộ ${aptCode.trim()} thành công!`);
      setAddAptOpen(false);
      setAptCode('');
      setAptFloor(1);
      setAptArea(70);
      setAptNote('');
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  // Handle Update Apartment
  const handleUpdateApartment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApt) return;
    try {
      await ApiClient.updateApartment(selectedApt.id, {
        floor: Number(editFloor),
        area_m2: Number(editArea),
        status: editStatus,
        note: editNote.trim() || undefined,
      });
      success(`Đã cập nhật căn hộ ${selectedApt.code} thành công!`);
      setEditAptOpen(false);
      setSelectedApt(null);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  // Handle Add Household
  const handleAddHousehold = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        household_code: hhCode.trim(),
        apartment_id: hhApartmentId ? Number(hhApartmentId) : undefined,
        contact_phone: hhPhone.trim() || undefined,
        contact_email: hhEmail.trim() || undefined,
        note: hhNote.trim() || undefined,
      };

      if (headName.trim()) {
        payload.head = {
          full_name: headName.trim(),
          date_of_birth: headDob,
          gender: headGender,
          cccd: headCccd.trim() || undefined,
          phone: headPhone.trim() || undefined,
          email: headEmail.trim() || undefined,
          relationship_to_head: 'CHỦ HỘ',
          is_head: true,
        };
      }

      const res = await ApiClient.createHousehold(payload);
      setAddHhOpen(false);
      setCreatedHhResult(res);
      success(`Đã khai báo hộ gia đình ${hhCode.trim()} thành công!`);
      loadData();

      // Reset form
      setHhCode('');
      setHhApartmentId('');
      setHhPhone('');
      setHhEmail('');
      setHhNote('');
      setHeadName('');
      setHeadCccd('');
      setHeadPhone('');
      setHeadEmail('');
    } catch (err: any) {
      toastError(err.message);
    }
  };

  // Handle Deactivate Household
  const handleDeactivateHousehold = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetHh) return;
    try {
      await ApiClient.deactivateHousehold(targetHh.id, deactivateReason.trim());
      success(`Đã ngừng quản lý hộ gia đình ${targetHh.household_code} thành công!`);
      setDeactivateOpen(false);
      setTargetHh(null);
      setDeactivateReason('');
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  // Handle Transfer Apartment
  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transferSourceHh || !transferTargetHhId) return;
    try {
      await ApiClient.transferApartment(transferSourceHh.id, {
        new_household_id: Number(transferTargetHhId),
        effective_date: transferDate,
        reason: transferReason.trim() || undefined,
      });
      success(`Chuyển nhượng căn hộ thành công! Hồ sơ cư trú mới đã có hiệu lực (US-03).`);
      setTransferOpen(false);
      setTransferSourceHh(null);
      setTransferTargetHhId('');
      setTransferReason('');
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  // Filtered Apartments
  const filteredApartments = apartments.filter((apt) => {
    const matchSearch = apt.code.toLowerCase().includes(aptSearch.toLowerCase());
    const matchFloor = aptFloorFilter === 'ALL' || String(apt.floor) === aptFloorFilter;
    const matchStatus = aptStatusFilter === 'ALL' || apt.status === aptStatusFilter;
    return matchSearch && matchFloor && matchStatus;
  });

  // Filtered Households
  const filteredHouseholds = households.filter((hh) => {
    const matchSearch =
      hh.household_code.toLowerCase().includes(hhSearch.toLowerCase()) ||
      (hh.head_name && hh.head_name.toLowerCase().includes(hhSearch.toLowerCase())) ||
      (hh.apartment_code && hh.apartment_code.toLowerCase().includes(hhSearch.toLowerCase()));
    const matchStatus = hhStatusFilter === 'ALL' || hh.status === hhStatusFilter;
    return matchSearch && matchStatus;
  });

  const availableFloors = Array.from(new Set(apartments.map((a) => a.floor))).sort((a, b) => a - b);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Building2 className="w-6 h-6 text-blue-600" />
            <span>Quản lý Căn hộ & Hộ gia đình (Sprint 1: US-01, US-02, US-03)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Khai báo căn hộ vật lý, danh sách hộ gia đình cư trú, chuyển nhượng và bàn giao theo quy trình chuẩn.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            isLoading={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
          {activeTab === 'apartments' ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setAddAptOpen(true)}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              Thêm căn hộ mới
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setAddHhOpen(true)}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              Khai báo hộ gia đình
            </Button>
          )}
        </div>
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
          <Button size="sm" variant="outline" onClick={loadData}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('apartments')}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'apartments'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Home className="w-4 h-4" />
          <span>Danh sách Căn hộ ({apartments.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('households')}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'households'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Danh sách Hộ gia đình ({households.length})</span>
        </button>
      </div>

      {/* TAB 1: APARTMENTS */}
      {activeTab === 'apartments' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
            <Input
              placeholder="Tìm mã căn hộ (VD: P.1001)..."
              value={aptSearch}
              onChange={(e) => setAptSearch(e.target.value)}
              icon={<Search className="w-4 h-4" />}
            />

            <div>
              <select
                value={aptFloorFilter}
                onChange={(e) => setAptFloorFilter(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả các tầng</option>
                {availableFloors.map((fl) => (
                  <option key={fl} value={String(fl)}>
                    Tầng {fl}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <select
                value={aptStatusFilter}
                onChange={(e) => setAptStatusFilter(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả trạng thái</option>
                <option value="ACTIVE">Đang hoạt động (ACTIVE)</option>
                <option value="INACTIVE">Ngừng hoạt động (INACTIVE)</option>
              </select>
            </div>
          </div>

          {/* Apartments Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Mã Căn Hộ</th>
                    <th className="py-3 px-4">Tầng</th>
                    <th className="py-3 px-4">Diện tích sàn</th>
                    <th className="py-3 px-4">Ghi chú</th>
                    <th className="py-3 px-4 text-center">Trạng thái</th>
                    <th className="py-3 px-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredApartments.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        {loading ? 'Đang tải dữ liệu căn hộ...' : 'Không tìm thấy căn hộ phù hợp.'}
                      </td>
                    </tr>
                  ) : (
                    filteredApartments.map((apt) => (
                      <tr key={apt.id} className="hover:bg-slate-50">
                        <td className="py-3.5 px-4 font-mono font-bold text-blue-700">{apt.code}</td>
                        <td className="py-3.5 px-4 font-medium text-slate-800">Tầng {apt.floor}</td>
                        <td className="py-3.5 px-4 font-semibold text-slate-900">{apt.area_m2} m²</td>
                        <td className="py-3.5 px-4 text-slate-500">{apt.note || '---'}</td>
                        <td className="py-3.5 px-4 text-center">
                          <Badge variant={apt.status === 'ACTIVE' ? 'success' : 'danger'} dot size="sm">
                            {apt.status === 'ACTIVE' ? 'Hoạt động' : 'Tạm khóa'}
                          </Badge>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => {
                              setSelectedApt(apt);
                              setEditFloor(apt.floor);
                              setEditArea(apt.area_m2);
                              setEditStatus(apt.status);
                              setEditNote(apt.note || '');
                              setEditAptOpen(true);
                            }}
                            className="text-xs font-semibold text-blue-600 hover:text-blue-800 p-1 rounded transition"
                          >
                            Chỉnh sửa
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: HOUSEHOLDS */}
      {activeTab === 'households' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
            <Input
              placeholder="Tìm theo mã hộ, tên chủ hộ, căn hộ..."
              value={hhSearch}
              onChange={(e) => setHhSearch(e.target.value)}
              icon={<Search className="w-4 h-4" />}
            />

            <div>
              <select
                value={hhStatusFilter}
                onChange={(e) => setHhStatusFilter(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả trạng thái</option>
                <option value="ACTIVE">Đang cư trú (ACTIVE)</option>
                <option value="INACTIVE">Đã chuyển đi (INACTIVE)</option>
              </select>
            </div>
          </div>

          {/* Households Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Mã Hộ</th>
                    <th className="py-3 px-4">Căn Hộ</th>
                    <th className="py-3 px-4">Chủ Hộ Đại Diện</th>
                    <th className="py-3 px-4">Liên hệ</th>
                    <th className="py-3 px-4 text-center">Số nhân khẩu</th>
                    <th className="py-3 px-4 text-center">Trạng thái</th>
                    <th className="py-3 px-4 text-right">Thao tác nghiệp vụ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredHouseholds.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        {loading ? 'Đang tải danh sách hộ gia đình...' : 'Không có hộ gia đình nào.'}
                      </td>
                    </tr>
                  ) : (
                    filteredHouseholds.map((hh) => (
                      <tr key={hh.id} className="hover:bg-slate-50">
                        <td className="py-3.5 px-4 font-mono font-bold text-blue-700">{hh.household_code}</td>
                        <td className="py-3.5 px-4 font-semibold text-slate-800">
                          {hh.apartment_code ? (
                            <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md font-mono">
                              {hh.apartment_code}
                            </span>
                          ) : (
                            <span className="text-slate-400">Chưa gán</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 font-medium text-slate-900">
                          {hh.head_name || <span className="text-slate-400">Chưa khai báo</span>}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">
                          <p>{hh.contact_phone || hh.head_phone || '---'}</p>
                          {hh.contact_email && (
                            <p className="text-[11px] text-slate-400">{hh.contact_email}</p>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-center font-semibold text-slate-800">
                          {hh.member_count} người
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <Badge variant={hh.status === 'ACTIVE' ? 'success' : 'danger'} dot size="sm">
                            {hh.status === 'ACTIVE' ? 'Đang ở' : 'Đã dừng'}
                          </Badge>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {hh.status === 'ACTIVE' && (
                              <>
                                <button
                                  onClick={() => {
                                    setTransferSourceHh(hh);
                                    setTransferOpen(true);
                                  }}
                                  className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50 transition"
                                  title="Chuyển nhượng căn hộ sang hộ khác (US-03)"
                                >
                                  Chuyển nhượng
                                </button>
                                <button
                                  onClick={() => {
                                    setTargetHh(hh);
                                    setDeactivateOpen(true);
                                  }}
                                  className="text-[11px] font-semibold text-rose-600 hover:text-rose-800 px-2 py-1 rounded hover:bg-rose-50 transition"
                                  title="Ngừng quản lý hộ gia đình (US-02)"
                                >
                                  Ngừng quản lý
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Thêm căn hộ mới */}
      <Modal
        isOpen={addAptOpen}
        onClose={() => setAddAptOpen(false)}
        title="Khai báo căn hộ mới (US-01)"
        description="Đăng ký mã căn hộ và diện tích thực tế vào cơ sở dữ liệu."
      >
        <form onSubmit={handleAddApartment} className="space-y-4">
          <Input
            label="Mã căn hộ"
            placeholder="Ví dụ: P.1001, B.1204..."
            value={aptCode}
            onChange={(e) => setAptCode(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Số tầng"
              type="number"
              min="0"
              value={aptFloor}
              onChange={(e) => setAptFloor(Number(e.target.value))}
              required
            />
            <Input
              label="Diện tích (m²)"
              type="number"
              step="0.1"
              min="1"
              value={aptArea}
              onChange={(e) => setAptArea(Number(e.target.value))}
              required
            />
          </div>

          <Input
            label="Ghi chú căn hộ"
            placeholder="Ví dụ: Căn hộ góc, 2 phòng ngủ..."
            value={aptNote}
            onChange={(e) => setAptNote(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddAptOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu căn hộ
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Chỉnh sửa căn hộ */}
      <Modal
        isOpen={editAptOpen}
        onClose={() => setEditAptOpen(false)}
        title={`Chỉnh sửa căn hộ ${selectedApt?.code}`}
        description="Cập nhật thông số diện tích, tầng và trạng thái căn hộ."
      >
        <form onSubmit={handleUpdateApartment} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Số tầng"
              type="number"
              min="0"
              value={editFloor}
              onChange={(e) => setEditFloor(Number(e.target.value))}
              required
            />
            <Input
              label="Diện tích (m²)"
              type="number"
              step="0.1"
              min="1"
              value={editArea}
              onChange={(e) => setEditArea(Number(e.target.value))}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Trạng thái</label>
            <select
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value as any)}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="ACTIVE">Hoạt động (ACTIVE)</option>
              <option value="INACTIVE">Tạm khóa (INACTIVE)</option>
            </select>
          </div>

          <Input
            label="Ghi chú"
            value={editNote}
            onChange={(e) => setEditNote(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setEditAptOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu thay đổi
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Khai báo hộ gia đình mới */}
      <Modal
        isOpen={addHhOpen}
        onClose={() => setAddHhOpen(false)}
        title="Khai báo hộ gia đình mới (US-01, AC-30.2)"
        description="Tạo hồ sơ hộ gia đình và tự động cấp tài khoản truy cập Cư dân."
      >
        <form onSubmit={handleAddHousehold} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Mã hộ gia đình"
              placeholder="Ví dụ: HO-1001, HO-B1204..."
              value={hhCode}
              onChange={(e) => setHhCode(e.target.value)}
              required
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Gán căn hộ</label>
              <select
                value={hhApartmentId}
                onChange={(e) => setHhApartmentId(e.target.value ? Number(e.target.value) : '')}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="">-- Chưa gán căn hộ --</option>
                {apartments
                  .filter((a) => a.status === 'ACTIVE')
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} (Tầng {a.floor} - {a.area_m2}m²)
                    </option>
                  ))}
              </select>
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
            <p className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-blue-600" />
              <span>Thông tin chủ hộ đại diện (Tùy chọn)</span>
            </p>

            <Input
              label="Họ và tên chủ hộ"
              placeholder="Ví dụ: Nguyễn Văn A"
              value={headName}
              onChange={(e) => setHeadName(e.target.value)}
            />

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Ngày sinh"
                type="date"
                value={headDob}
                onChange={(e) => setHeadDob(e.target.value)}
              />
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Giới tính</label>
                <select
                  value={headGender}
                  onChange={(e) => setHeadGender(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
                >
                  <option value="NAM">Nam</option>
                  <option value="NU">Nữ</option>
                  <option value="KHAC">Khác</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Số CCCD/CMND"
                placeholder="9-12 chữ số"
                value={headCccd}
                onChange={(e) => setHeadCccd(e.target.value)}
              />
              <Input
                label="Số điện thoại"
                placeholder="0912..."
                value={headPhone}
                onChange={(e) => setHeadPhone(e.target.value)}
              />
            </div>
          </div>

          <Input
            label="Ghi chú về hộ gia đình"
            placeholder="Ghi chú thêm..."
            value={hhNote}
            onChange={(e) => setHhNote(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddHhOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Xác nhận khai báo
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Kết quả tạo hộ & Tài khoản Cư dân (AC-30.2) */}
      {createdHhResult && (
        <Modal
          isOpen={true}
          onClose={() => setCreatedHhResult(null)}
          title="Tạo hộ gia đình thành công!"
          description="Thông tin tài khoản cư dân đã được hệ thống tự động khởi tạo."
        >
          <div className="space-y-4">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs text-emerald-900 flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Đã lưu hồ sơ hộ gia đình {createdHhResult.household_code}</p>
                <p className="mt-0.5">
                  Căn hộ: {createdHhResult.apartment_code || 'Chưa gán'} • Chủ hộ: {createdHhResult.head_name || 'Chưa có'}
                </p>
              </div>
            </div>

            {createdHhResult.resident_account && (
              <div className="p-4 bg-slate-900 text-white rounded-2xl space-y-2 text-xs">
                <p className="font-bold text-amber-400 uppercase tracking-wider text-[11px]">
                  Tài khoản Cư Dân tự động cấp (US-30.2):
                </p>
                <div className="flex justify-between items-center py-1 border-b border-slate-800">
                  <span className="text-slate-400">Tên đăng nhập:</span>
                  <span className="font-mono font-bold text-white">{createdHhResult.resident_account.username}</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-slate-400">Mật khẩu tạm thời:</span>
                  <span className="font-mono font-bold text-emerald-400 text-sm">
                    {createdHhResult.resident_account.temporary_password}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 italic pt-1">
                  * Vui lòng bàn giao mật khẩu này cho chủ hộ. Cư dân sẽ được yêu cầu đổi mật khẩu ở lần đăng nhập đầu tiên.
                </p>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button variant="primary" onClick={() => setCreatedHhResult(null)}>
                Đã ghi nhận & Đóng
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Chuyển nhượng căn hộ (US-03) */}
      <Modal
        isOpen={transferOpen}
        onClose={() => setTransferOpen(false)}
        title="Chuyển nhượng quyền cư trú căn hộ (US-03)"
        description={`Chuyển nhượng căn hộ ${transferSourceHh?.apartment_code} từ hộ ${transferSourceHh?.household_code} sang hộ mới.`}
      >
        <form onSubmit={handleTransfer} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Hộ gia đình nhận chuyển nhượng
            </label>
            <select
              value={transferTargetHhId}
              onChange={(e) => setTransferTargetHhId(e.target.value ? Number(e.target.value) : '')}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              <option value="">-- Chọn hộ gia đình mới --</option>
              {households
                .filter((h) => h.id !== transferSourceHh?.id && h.status === 'ACTIVE')
                .map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.household_code} - {h.head_name || 'Chưa rõ chủ hộ'}
                  </option>
                ))}
            </select>
          </div>

          <Input
            label="Ngày có hiệu lực chuyển nhượng"
            type="date"
            value={transferDate}
            onChange={(e) => setTransferDate(e.target.value)}
            required
          />

          <Input
            label="Lý do chuyển nhượng"
            placeholder="Ví dụ: Chuyển nhượng hợp đồng mua bán căn hộ..."
            value={transferReason}
            onChange={(e) => setTransferReason(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setTransferOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Xác nhận chuyển nhượng
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Ngừng quản lý hộ gia đình (US-02) */}
      <Modal
        isOpen={deactivateOpen}
        onClose={() => setDeactivateOpen(false)}
        title="Ngừng quản lý hộ gia đình (US-02)"
        description={`Bạn có chắc muốn chuyển trạng thái hộ ${targetHh?.household_code} sang ngừng hoạt động (INACTIVE)?`}
      >
        <form onSubmit={handleDeactivateHousehold} className="space-y-4">
          <Input
            label="Lý do ngừng quản lý"
            placeholder="Ví dụ: Hộ gia đình đã bán nhà và chuyển đi..."
            value={deactivateReason}
            onChange={(e) => setDeactivateReason(e.target.value)}
            required
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setDeactivateOpen(false)}>
              Hủy
            </Button>
            <Button variant="danger" type="submit">
              Xác nhận ngừng quản lý
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
