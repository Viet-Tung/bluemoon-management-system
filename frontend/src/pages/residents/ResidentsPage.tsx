import React, { useEffect, useState, useCallback } from 'react';
import {
  Users,
  Plus,
  RefreshCw,
  AlertCircle,
  Search,
  Pencil,
  Trash2,
  Eye,
  FileSpreadsheet,
  UserCheck,
  Building2,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { ApiClient } from '../../api';
import { Household, Resident } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { ExcelImportModal } from '../../components/common/ExcelImportModal';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 20;

const calculateAge = (dobStr: string): number | null => {
  if (!dobStr) return null;
  const dob = new Date(dobStr);
  if (isNaN(dob.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const m = today.getMonth() - dob.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
    age--;
  }
  return age;
};

export const ResidentsPage: React.FC = () => {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('ADMIN');
  const { success, error: toastError } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // Households list & selected household
  const [households, setHouseholds] = useState<Household[]>([]);
  const [hhSearch, setHhSearch] = useState('');
  const [debouncedHhSearch, setDebouncedHhSearch] = useState('');
  const [selectedHouseholdId, setSelectedHouseholdId] = useState<number | null>(() => {
    const param = searchParams.get('household_id');
    return param ? Number(param) : null;
  });
  const [selectedHousehold, setSelectedHousehold] = useState<Household | null>(null);

  // Residents list state
  const [residents, setResidents] = useState<Resident[]>([]);
  const [totalResidents, setTotalResidents] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [includeDeleted, setIncludeDeleted] = useState(false);

  const [loadingHouseholds, setLoadingHouseholds] = useState(false);
  const [loadingResidents, setLoadingResidents] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Import Excel modal (ADMIN only)
  const [importOpen, setImportOpen] = useState(
    () => isAdmin && searchParams.get('import') === '1'
  );

  // Create Resident Modal
  const [addOpen, setAddOpen] = useState(false);
  const [fullName, setFullName] = useState('');
  const [dob, setDob] = useState('1995-01-01');
  const [gender, setGender] = useState('NAM');
  const [cccd, setCccd] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [relationship, setRelationship] = useState('');
  const [isHead, setIsHead] = useState(false);

  // Edit Resident Modal
  const [editOpen, setEditOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Resident | null>(null);
  const [editName, setEditName] = useState('');
  const [editDob, setEditDob] = useState('');
  const [editGender, setEditGender] = useState('NAM');
  const [editCccd, setEditCccd] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editRelationship, setEditRelationship] = useState('');

  // Detail Modal
  const [detailResident, setDetailResident] = useState<Resident | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Delete Resident Modal
  const [deleteTarget, setDeleteTarget] = useState<Resident | null>(null);
  const [deleteReason, setDeleteReason] = useState('');

  const [hasAutoSelected, setHasAutoSelected] = useState(false);

  // Sync URL parameter when household_id changes externally (e.g., from Omnibox)
  useEffect(() => {
    const paramId = searchParams.get('household_id');
    if (paramId) {
      const parsed = Number(paramId);
      if (!isNaN(parsed)) {
        setHasAutoSelected(true);
        setSelectedHouseholdId(parsed);
        setPage(1);
      }
    }
  }, [searchParams]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedHhSearch(hhSearch.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [hhSearch]);

  const loadHouseholds = useCallback(async () => {
    setLoadingHouseholds(true);
    try {
      const items = await ApiClient.fetchAllPages((pageIdx, pageSize) =>
        ApiClient.getHouseholds({
          page: pageIdx,
          page_size: pageSize,
          q: debouncedHhSearch || undefined,
        })
      );
      setHouseholds(items);
    } catch (err: any) {
      toastError(err.message || 'Không thể tải danh sách hộ gia đình.');
    } finally {
      setLoadingHouseholds(false);
    }
  }, [debouncedHhSearch, toastError]);

  useEffect(() => {
    if (
      !hasAutoSelected &&
      !selectedHouseholdId &&
      !searchParams.get('household_id') &&
      households.length > 0
    ) {
      const firstActive = households.find((h) => h.status === 'ACTIVE') || households[0];
      setSelectedHouseholdId(firstActive.id);
      setHasAutoSelected(true);
    }
  }, [hasAutoSelected, selectedHouseholdId, searchParams, households]);

  useEffect(() => {
    loadHouseholds();
  }, [loadHouseholds]);

  const loadSelectedHouseholdInfo = useCallback(async () => {
    if (!selectedHouseholdId) {
      setSelectedHousehold(null);
      return;
    }
    const found = households.find((h) => h.id === selectedHouseholdId);
    if (found) {
      setSelectedHousehold(found);
      return;
    }
    try {
      const hh = await ApiClient.getHousehold(selectedHouseholdId);
      setSelectedHousehold(hh);
    } catch {
      setSelectedHousehold(null);
    }
  }, [selectedHouseholdId, households]);

  useEffect(() => {
    loadSelectedHouseholdInfo();
  }, [loadSelectedHouseholdInfo]);

  const loadResidents = useCallback(async () => {
    if (!selectedHouseholdId) {
      setResidents([]);
      setTotalResidents(0);
      return;
    }
    setLoadingResidents(true);
    setErrorMessage(null);
    try {
      const res = await ApiClient.getHouseholdResidents(selectedHouseholdId, {
        page,
        page_size: PAGE_SIZE,
        residence_status: statusFilter !== 'ALL' ? statusFilter : undefined,
        include_deleted: isAdmin ? includeDeleted : undefined,
      });
      setResidents(res.items || []);
      setTotalResidents(res.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách nhân khẩu của hộ.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoadingResidents(false);
    }
  }, [selectedHouseholdId, page, statusFilter, includeDeleted, isAdmin, toastError]);

  useEffect(() => {
    loadResidents();
  }, [loadResidents]);

  const handleSelectHousehold = (idStr: string) => {
    const id = idStr ? Number(idStr) : null;
    setHasAutoSelected(true);
    setSelectedHouseholdId(id);
    setPage(1);
    if (id) {
      setSearchParams({ household_id: String(id) });
    } else {
      setSearchParams({});
    }
  };

  const handleAddResident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedHouseholdId) return;

    const age = calculateAge(dob);
    const trimmedCccd = cccd.trim();
    if (age !== null && age >= 14) {
      if (!/^[0-9]{9,12}$/.test(trimmedCccd)) {
        toastError('Nhân khẩu từ 14 tuổi trở lên bắt buộc nhập CCCD/CMND hợp lệ (9–12 chữ số).');
        return;
      }
    } else if (trimmedCccd && !/^[0-9]{9,12}$/.test(trimmedCccd)) {
      toastError('CCCD/CMND phải gồm từ 9 đến 12 chữ số.');
      return;
    }

    try {
      await ApiClient.createResident(selectedHouseholdId, {
        full_name: fullName.trim(),
        date_of_birth: dob,
        gender,
        cccd: trimmedCccd || undefined,
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
        relationship_to_head: relationship.trim() || (isHead ? 'Chủ hộ' : undefined),
        is_head: isHead,
      });
      success(`Đã thêm nhân khẩu "${fullName.trim()}" vào hộ gia đình!`);
      setAddOpen(false);
      setFullName('');
      setCccd('');
      setPhone('');
      setEmail('');
      setRelationship('');
      setIsHead(false);
      loadResidents();
      loadHouseholds();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleEditResident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;

    const age = calculateAge(editDob);
    const trimmedCccd = editCccd.trim();
    if (age !== null && age >= 14) {
      if (!/^[0-9]{9,12}$/.test(trimmedCccd)) {
        toastError('Nhân khẩu từ 14 tuổi trở lên bắt buộc nhập CCCD/CMND hợp lệ (9–12 chữ số).');
        return;
      }
    } else if (trimmedCccd && !/^[0-9]{9,12}$/.test(trimmedCccd)) {
      toastError('CCCD/CMND phải gồm từ 9 đến 12 chữ số.');
      return;
    }

    try {
      await ApiClient.updateResident(editTarget.id, {
        full_name: editName.trim(),
        date_of_birth: editDob,
        gender: editGender,
        cccd:
          (age !== null && age < 14) || trimmedCccd !== (editTarget.cccd || '')
            ? trimmedCccd
            : undefined,
        phone: editPhone.trim(),
        email: editEmail.trim(),
        relationship_to_head: editRelationship.trim(),
      });
      success(`Đã cập nhật thông tin nhân khẩu "${editName.trim()}"!`);
      setEditOpen(false);
      setEditTarget(null);
      loadResidents();
      loadHouseholds();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleOpenDetail = async (id: number) => {
    setLoadingDetail(true);
    try {
      const detail = await ApiClient.getResident(id);
      setDetailResident(detail);
    } catch (err: any) {
      toastError(err.message || 'Không thể tải chi tiết nhân khẩu.');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDeleteResident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deleteTarget) return;
    try {
      await ApiClient.deleteResident(deleteTarget.id, deleteReason.trim() || undefined);
      success(`Đã xóa nhân khẩu "${deleteTarget.full_name}" khỏi danh sách hiện hành.`);
      setDeleteTarget(null);
      setDeleteReason('');
      loadResidents();
      loadHouseholds();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const getGenderLabel = (g: string) => {
    switch (g) {
      case 'NAM':
        return 'Nam';
      case 'NU':
        return 'Nữ';
      case 'KHAC':
        return 'Khác';
      default:
        return g;
    }
  };

  const getStatusBadge = (r: Resident) => {
    if (r.is_deleted) {
      return <Badge variant="danger" size="sm">Đã xóa</Badge>;
    }
    switch (r.residence_status) {
      case 'THUONG_TRU':
        return <Badge variant="thuong_tru" dot size="sm">Thường trú</Badge>;
      case 'TAM_VANG':
        return <Badge variant="tam_vang" dot size="sm">Tạm vắng</Badge>;
      case 'DA_CHUYEN_DI':
        return <Badge variant="neutral" dot size="sm">Đã chuyển đi</Badge>;
      default:
        return <Badge size="sm">{r.residence_status}</Badge>;
    }
  };

  const addAge = calculateAge(dob);
  const editAge = calculateAge(editDob);
  const totalPages = Math.max(1, Math.ceil(totalResidents / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-600" />
            <span>Quản lý Nhân khẩu & Nhập liệu Excel</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Tra cứu, bổ sung, chỉnh sửa hồ sơ nhân khẩu theo hộ gia đình và nhập danh sách hàng loạt từ Excel.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              loadHouseholds();
              loadResidents();
            }}
            isLoading={loadingResidents || loadingHouseholds}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
          {isAdmin && (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setImportOpen(true)}
                icon={<FileSpreadsheet className="w-3.5 h-3.5 text-emerald-700" />}
              >
                Nhập từ Excel (.xlsx)
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!selectedHouseholdId}
                onClick={() => setAddOpen(true)}
                icon={<Plus className="w-3.5 h-3.5" />}
              >
                Thêm nhân khẩu
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Household Selector & Summary */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Input
            label="Tìm nhanh hộ gia đình"
            placeholder="Nhập mã hộ, tên chủ hộ, SĐT..."
            value={hhSearch}
            onChange={(e) => setHhSearch(e.target.value)}
            icon={<Search className="w-4 h-4" />}
          />

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Chọn hộ gia đình
            </label>
            <select
              value={selectedHouseholdId || ''}
              onChange={(e) => handleSelectHousehold(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">-- Chọn hộ gia đình cần xem --</option>
              {households.map((hh) => (
                <option key={hh.id} value={hh.id}>
                  {hh.household_code} {hh.apartment_code ? `(${hh.apartment_code})` : ''} -{' '}
                  {hh.head_name || 'Chưa rõ chủ hộ'} [{hh.member_count} người]
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedHousehold && (
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Mã hộ gia đình</span>
              <span className="font-mono font-bold text-blue-700">
                {selectedHousehold.household_code}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Căn hộ đang ở</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5 text-slate-400" />
                {selectedHousehold.apartment_code || 'Chưa gán'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Chủ hộ đại diện</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1">
                <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                {selectedHousehold.head_name || 'Chưa khai báo'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Trạng thái & Quy mô</span>
              <div className="flex items-center gap-2 mt-0.5">
                <Badge
                  variant={selectedHousehold.status === 'ACTIVE' ? 'success' : 'danger'}
                  size="sm"
                >
                  {selectedHousehold.status === 'ACTIVE' ? 'Đang ở' : 'Đã dừng'}
                </Badge>
                <span className="font-semibold text-slate-700">
                  {selectedHousehold.member_count} nhân khẩu
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Không thể tải dữ liệu nhân khẩu</p>
              <p className="text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={loadResidents}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Residents Filters */}
      <div className="bg-white p-3 rounded-2xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả trạng thái cư trú</option>
            <option value="THUONG_TRU">Thường trú</option>
            <option value="TAM_VANG">Tạm vắng</option>
            <option value="DA_CHUYEN_DI">Đã chuyển đi</option>
          </select>

          {isAdmin && (
            <label className="inline-flex items-center gap-2 text-xs text-slate-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeDeleted}
                onChange={(e) => {
                  setIncludeDeleted(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Hiển thị nhân khẩu đã xóa</span>
            </label>
          )}
        </div>

        <span className="text-xs text-slate-500 font-mono">
          Tổng số nhân khẩu: {totalResidents}
        </span>
      </div>

      {/* Residents Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Họ và tên</th>
                <th className="py-3 px-4">Ngày sinh</th>
                <th className="py-3 px-4">Giới tính</th>
                <th className="py-3 px-4">Số CCCD/CMND</th>
                <th className="py-3 px-4">Liên hệ</th>
                <th className="py-3 px-4">Quan hệ</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {!selectedHouseholdId ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    Vui lòng chọn một hộ gia đình để xem danh sách nhân khẩu.
                  </td>
                </tr>
              ) : residents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    {loadingResidents
                      ? 'Đang tải danh sách nhân khẩu...'
                      : 'Chưa có nhân khẩu nào trong hộ gia đình này.'}
                  </td>
                </tr>
              ) : (
                residents.map((r) => (
                  <tr
                    key={r.id}
                    className={`hover:bg-slate-50 ${r.is_deleted ? 'opacity-60 bg-slate-50/60' : ''}`}
                  >
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <span>{r.full_name}</span>
                        {r.is_head && (
                          <Badge variant="info" size="sm">
                            Chủ hộ
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600">{r.date_of_birth}</td>
                    <td className="py-3.5 px-4 text-slate-700">{getGenderLabel(r.gender)}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-700">{r.cccd || '---'}</td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <p>{r.phone || '---'}</p>
                      {r.email && <p className="text-[11px] text-slate-400">{r.email}</p>}
                    </td>
                    <td className="py-3.5 px-4 text-slate-700">
                      {r.relationship_to_head || (r.is_head ? 'Chủ hộ' : '---')}
                    </td>
                    <td className="py-3.5 px-4 text-center">{getStatusBadge(r)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenDetail(r.id)}
                          disabled={loadingDetail}
                          className="p-1.5 rounded-lg text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition"
                          title="Xem chi tiết"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        {isAdmin && !r.is_deleted && (
                          <>
                            <button
                              onClick={() => {
                                setEditTarget(r);
                                setEditName(r.full_name);
                                setEditDob(r.date_of_birth);
                                setEditGender(r.gender);
                                setEditCccd(r.cccd || '');
                                setEditPhone(r.phone || '');
                                setEditEmail(r.email || '');
                                setEditRelationship(r.relationship_to_head || '');
                                setEditOpen(true);
                              }}
                              className="p-1.5 rounded-lg text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition"
                              title="Chỉnh sửa nhân khẩu"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => {
                                setDeleteTarget(r);
                                setDeleteReason('');
                              }}
                              className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 transition"
                              title="Xóa nhân khẩu"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
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

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
          <span>
            Trang {page} / {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loadingResidents}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Trang trước
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loadingResidents}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Trang sau
            </Button>
          </div>
        </div>
      </div>

      {/* Modal: Thêm nhân khẩu */}
      <Modal
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        title="Thêm nhân khẩu mới"
        description={`Thêm thành viên mới vào hộ ${selectedHousehold?.household_code || ''}.`}
      >
        <form onSubmit={handleAddResident} className="space-y-4">
          <Input
            label="Họ và tên"
            placeholder="Ví dụ: Nguyễn Văn B"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Ngày sinh"
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              required
            />
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Giới tính <span className="text-rose-500">*</span>
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="NAM">Nam</option>
                <option value="NU">Nữ</option>
                <option value="KHAC">Khác</option>
              </select>
            </div>
          </div>

          <Input
            label="Số CCCD/CMND"
            placeholder={
              addAge !== null && addAge < 14
                ? 'Không bắt buộc với trẻ dưới 14 tuổi'
                : '9–12 chữ số (Bắt buộc từ 14 tuổi)'
            }
            value={cccd}
            onChange={(e) => setCccd(e.target.value)}
            required={addAge !== null && addAge >= 14}
            helperText={
              addAge !== null
                ? addAge >= 14
                  ? `Tuổi hiện tại: ${addAge} tuổi — Bắt buộc có số CCCD/CMND (9–12 chữ số).`
                  : `Tuổi hiện tại: ${addAge} tuổi — Có thể để trống CCCD/CMND.`
                : undefined
            }
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Số điện thoại"
              placeholder="0912345678"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <Input
              label="Email"
              type="email"
              placeholder="email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <Input
            label="Quan hệ với chủ hộ"
            placeholder="Ví dụ: Vợ, Con, Bố, Mẹ..."
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
          />

          <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={isHead}
              onChange={(e) => setIsHead(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Đặt làm chủ hộ (Chỉ dùng nếu hộ hiện chưa có chủ hộ)</span>
          </label>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu nhân khẩu
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Chỉnh sửa nhân khẩu */}
      <Modal
        isOpen={editOpen}
        onClose={() => setEditOpen(false)}
        title={`Cập nhật nhân khẩu: ${editTarget?.full_name || ''}`}
        description="Cập nhật thông tin cá nhân của nhân khẩu. Để thay đổi chủ hộ, hãy thao tác tại màn hình Hộ gia đình."
      >
        <form onSubmit={handleEditResident} className="space-y-4">
          <Input
            label="Họ và tên"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Ngày sinh"
              type="date"
              value={editDob}
              onChange={(e) => setEditDob(e.target.value)}
              required
            />
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Giới tính <span className="text-rose-500">*</span>
              </label>
              <select
                value={editGender}
                onChange={(e) => setEditGender(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="NAM">Nam</option>
                <option value="NU">Nữ</option>
                <option value="KHAC">Khác</option>
              </select>
            </div>
          </div>

          <Input
            label="Số CCCD/CMND"
            placeholder="9–12 chữ số"
            value={editCccd}
            onChange={(e) => setEditCccd(e.target.value)}
            required={editAge !== null && editAge >= 14}
            helperText={
              editAge !== null
                ? editAge >= 14
                  ? `Tuổi hiện tại: ${editAge} tuổi — Bắt buộc có CCCD/CMND (9–12 chữ số).`
                  : `Tuổi hiện tại: ${editAge} tuổi — Có thể để trống CCCD/CMND.`
                : undefined
            }
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Số điện thoại"
              value={editPhone}
              onChange={(e) => setEditPhone(e.target.value)}
            />
            <Input
              label="Email"
              type="email"
              value={editEmail}
              onChange={(e) => setEditEmail(e.target.value)}
            />
          </div>

          <Input
            label="Quan hệ với chủ hộ"
            value={editRelationship}
            onChange={(e) => setEditRelationship(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setEditOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu thay đổi
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Chi tiết nhân khẩu */}
      {detailResident && (
        <Modal
          isOpen={true}
          onClose={() => setDetailResident(null)}
          title={`Hồ sơ nhân khẩu: ${detailResident.full_name}`}
          description={`Mã nhân khẩu #${detailResident.id}`}
        >
          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3 p-4 bg-slate-50 border border-slate-200 rounded-2xl">
              <div>
                <span className="text-slate-400 block">Họ và tên</span>
                <span className="font-bold text-slate-900">{detailResident.full_name}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Vai trò trong hộ</span>
                <span className="font-semibold text-slate-800">
                  {detailResident.is_head
                    ? 'Chủ hộ'
                    : detailResident.relationship_to_head || 'Thành viên'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">Ngày sinh</span>
                <span className="font-mono text-slate-800">{detailResident.date_of_birth}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Giới tính</span>
                <span className="text-slate-800">{getGenderLabel(detailResident.gender)}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Số CCCD/CMND</span>
                <span className="font-mono text-slate-800">{detailResident.cccd || '---'}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Số điện thoại</span>
                <span className="font-mono text-slate-800">{detailResident.phone || '---'}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Email</span>
                <span className="text-slate-800">{detailResident.email || '---'}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Trạng thái cư trú</span>
                <div className="mt-0.5">{getStatusBadge(detailResident)}</div>
              </div>
              {detailResident.status_reason && (
                <div className="col-span-2">
                  <span className="text-slate-400 block">Ghi chú trạng thái</span>
                  <span className="text-slate-700">{detailResident.status_reason}</span>
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <Button variant="primary" size="sm" onClick={() => setDetailResident(null)}>
                Đóng
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Xóa mềm nhân khẩu */}
      {deleteTarget && (
        <Modal
          isOpen={true}
          onClose={() => setDeleteTarget(null)}
          title="Xác nhận xóa nhân khẩu"
          description={`Xóa nhân khẩu "${deleteTarget.full_name}" khỏi danh sách cư trú hiện hành (dữ liệu lịch sử vẫn được bảo toàn).`}
        >
          <form onSubmit={handleDeleteResident} className="space-y-4">
            {deleteTarget.is_head && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900">
                Nhân khẩu này đang là chủ hộ. Nếu hộ đang hoạt động, vui lòng đổi chủ hộ trước khi xóa.
              </div>
            )}

            <Input
              label="Lý do xóa (Tùy chọn)"
              placeholder="Ví dụ: Nhập nhầm thông tin, đã chuyển khẩu..."
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
            />

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button variant="outline" type="button" onClick={() => setDeleteTarget(null)}>
                Hủy
              </Button>
              <Button variant="danger" type="submit">
                Xác nhận xóa
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Import Excel */}
      {isAdmin && (
        <ExcelImportModal
          isOpen={importOpen}
          onClose={() => setImportOpen(false)}
          onSuccess={() => {
            loadHouseholds();
            loadResidents();
          }}
        />
      )}
    </div>
  );
};
