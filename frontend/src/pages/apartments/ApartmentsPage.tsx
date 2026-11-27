import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Building2,
  Plus,
  Search,
  Home,
  RefreshCw,
  AlertCircle,
  Users,
  UserCheck,
  CheckCircle,
  FileSpreadsheet,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiClient } from '../../api';
import { Apartment, Household, HouseholdCreated, Resident } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { ExcelImportModal } from '../../components/common/ExcelImportModal';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 20;

export const ApartmentsPage: React.FC = () => {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('ADMIN');
  const { success, error: toastError } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [activeTab, setActiveTab] = useState<'apartments' | 'households'>(() =>
    searchParams.get('tab') === 'households' ? 'households' : 'apartments'
  );
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Import Excel modal (ADMIN only)
  const [importOpen, setImportOpen] = useState(false);

  // Reference options for floor filter, cross-page search, and ADMIN modals
  const [allApartments, setAllApartments] = useState<Apartment[]>([]);
  const [allApartmentsLoaded, setAllApartmentsLoaded] = useState(false);
  const [allActiveHouseholds, setAllActiveHouseholds] = useState<Household[]>([]);

  // Apartments State
  const [apartments, setApartments] = useState<Apartment[]>([]);
  const [aptTotal, setAptTotal] = useState(0);
  const [aptPage, setAptPage] = useState(1);
  const [aptSearch, setAptSearch] = useState(() =>
    searchParams.get('tab') !== 'households' ? searchParams.get('q') || '' : ''
  );
  const [aptFloorFilter, setAptFloorFilter] = useState<string>('ALL');
  const [aptStatusFilter, setAptStatusFilter] = useState<string>('ALL');

  // Add Apartment Modal
  const [addAptOpen, setAddAptOpen] = useState(false);
  const [aptCode, setAptCode] = useState('');
  const [aptFloor, setAptFloor] = useState(1);
  const [aptArea, setAptArea] = useState('70');
  const [aptNote, setAptNote] = useState('');

  // Edit Apartment Modal
  const [editAptOpen, setEditAptOpen] = useState(false);
  const [selectedApt, setSelectedApt] = useState<Apartment | null>(null);
  const [editFloor, setEditFloor] = useState(1);
  const [editArea, setEditArea] = useState('70');
  const [editStatus, setEditStatus] = useState<'ACTIVE' | 'INACTIVE'>('ACTIVE');
  const [editNote, setEditNote] = useState('');

  // Households State
  const [households, setHouseholds] = useState<Household[]>([]);
  const [hhTotal, setHhTotal] = useState(0);
  const [hhPage, setHhPage] = useState(1);
  const [hhSearch, setHhSearch] = useState(() =>
    searchParams.get('tab') === 'households' ? searchParams.get('q') || '' : ''
  );
  const [debouncedHhSearch, setDebouncedHhSearch] = useState(hhSearch);
  const [hhStatusFilter, setHhStatusFilter] = useState<string>('ALL');

  // Add Household Modal
  const [addHhOpen, setAddHhOpen] = useState(false);
  const [hhCode, setHhCode] = useState('');
  const [hhApartmentId, setHhApartmentId] = useState<number | ''>('');
  const [hhPhone, setHhPhone] = useState('');
  const [hhEmail, setHhEmail] = useState('');
  const [hhNote, setHhNote] = useState('');
  const [headName, setHeadName] = useState('');
  const [headDob, setHeadDob] = useState('1990-01-01');
  const [headGender, setHeadGender] = useState('NAM');
  const [headCccd, setHeadCccd] = useState('');
  const [headPhone, setHeadPhone] = useState('');
  const [headEmail, setHeadEmail] = useState('');

  // Edit Household Modal
  const [editHhOpen, setEditHhOpen] = useState(false);
  const [editHhTarget, setEditHhTarget] = useState<Household | null>(null);
  const [editHhPhone, setEditHhPhone] = useState('');
  const [editHhEmail, setEditHhEmail] = useState('');
  const [editHhNote, setEditHhNote] = useState('');

  // Change Household Head Modal (populates household residents)
  const [changeHeadOpen, setChangeHeadOpen] = useState(false);
  const [changeHeadTarget, setChangeHeadTarget] = useState<Household | null>(null);
  const [headCandidates, setHeadCandidates] = useState<Resident[]>([]);
  const [loadingHeadCandidates, setLoadingHeadCandidates] = useState(false);
  const [newHeadResidentId, setNewHeadResidentId] = useState<number | ''>('');
  const [changeHeadDate, setChangeHeadDate] = useState<string>(
    () => new Date().toISOString().split('T')[0]
  );
  const [changeHeadReason, setChangeHeadReason] = useState('');

  // Created Household Result Modal
  const [createdHhResult, setCreatedHhResult] = useState<HouseholdCreated | null>(null);

  // Deactivate Household Modal
  const [deactivateOpen, setDeactivateOpen] = useState(false);
  const [targetHh, setTargetHh] = useState<Household | null>(null);
  const [deactivateReason, setDeactivateReason] = useState('');

  // Transfer Apartment Modal
  const [transferOpen, setTransferOpen] = useState(false);
  const [transferSourceHh, setTransferSourceHh] = useState<Household | null>(null);
  const [transferTargetHhId, setTransferTargetHhId] = useState<number | ''>('');
  const [transferDate, setTransferDate] = useState<string>(
    () => new Date().toISOString().split('T')[0]
  );
  const [transferReason, setTransferReason] = useState('');

  // Sync URL query params (from Omnibox navigation)
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    const qParam = searchParams.get('q');
    if (tabParam === 'households') {
      setActiveTab('households');
      if (qParam !== null) {
        setHhSearch(qParam);
        setDebouncedHhSearch(qParam);
        setHhPage(1);
      }
    } else if (tabParam === 'apartments') {
      setActiveTab('apartments');
      if (qParam !== null) {
        setAptSearch(qParam);
        setAptPage(1);
      }
    }
  }, [searchParams]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedHhSearch(hhSearch.trim());
      setHhPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [hhSearch]);

  const loadReferenceOptions = useCallback(async () => {
    try {
      const aptItems = await ApiClient.fetchAllPages((page, pageSize) =>
        ApiClient.getApartments({ page, page_size: pageSize })
      );
      setAllApartments(aptItems);
      setAllApartmentsLoaded(true);
    } catch {
      // Errors surfaced by main loaders
    }

    if (!isAdmin) return;
    try {
      const hhItems = await ApiClient.fetchAllPages((page, pageSize) =>
        ApiClient.getHouseholds({ page, page_size: pageSize, status: 'ACTIVE' })
      );
      setAllActiveHouseholds(hhItems);
    } catch {
      // Errors surfaced by main loaders
    }
  }, [isAdmin]);

  const loadApartments = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const aptRes = await ApiClient.getApartments({
        page: aptPage,
        page_size: PAGE_SIZE,
        floor: aptFloorFilter !== 'ALL' ? Number(aptFloorFilter) : undefined,
        status: aptStatusFilter !== 'ALL' ? aptStatusFilter : undefined,
      });
      setApartments(aptRes.items || []);
      setAptTotal(aptRes.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải dữ liệu căn hộ từ máy chủ.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [aptPage, aptFloorFilter, aptStatusFilter, toastError]);

  const loadHouseholds = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const hhRes = await ApiClient.getHouseholds({
        page: hhPage,
        page_size: PAGE_SIZE,
        q: debouncedHhSearch || undefined,
        status: hhStatusFilter !== 'ALL' ? hhStatusFilter : undefined,
      });
      setHouseholds(hhRes.items || []);
      setHhTotal(hhRes.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách hộ gia đình từ máy chủ.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [hhPage, debouncedHhSearch, hhStatusFilter, toastError]);

  const loadData = useCallback(async () => {
    await Promise.all([loadApartments(), loadHouseholds(), loadReferenceOptions()]);
  }, [loadApartments, loadHouseholds, loadReferenceOptions]);

  useEffect(() => {
    loadApartments();
  }, [loadApartments]);

  useEffect(() => {
    loadHouseholds();
  }, [loadHouseholds]);

  useEffect(() => {
    loadReferenceOptions();
  }, [loadReferenceOptions]);

  // Handle Add Apartment
  const handleAddApartment = async (e: React.FormEvent) => {
    e.preventDefault();
    const area = parseFloat(aptArea);
    if (isNaN(area) || area <= 0) {
      toastError('Diện tích sàn phải lớn hơn 0.');
      return;
    }
    try {
      await ApiClient.createApartment({
        code: aptCode.trim(),
        floor: Number(aptFloor),
        area_m2: area,
        note: aptNote.trim() || undefined,
      });
      success(`Đã thêm căn hộ ${aptCode.trim()} thành công!`);
      setAddAptOpen(false);
      setAptCode('');
      setAptFloor(1);
      setAptArea('70');
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
    const area = parseFloat(editArea);
    if (isNaN(area) || area <= 0) {
      toastError('Diện tích sàn phải lớn hơn 0.');
      return;
    }
    try {
      await ApiClient.updateApartment(selectedApt.id, {
        floor: Number(editFloor),
        area_m2: area,
        status: editStatus,
        note: editNote.trim(),
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
          relationship_to_head: 'Chủ hộ',
          is_head: true,
        };
      }

      const res = await ApiClient.createHousehold(payload);
      setAddHhOpen(false);
      setCreatedHhResult(res);
      success(`Đã khai báo hộ gia đình ${hhCode.trim()} thành công!`);
      loadData();

      setHhCode('');
      setHhApartmentId('');
      setHhPhone('');
      setHhEmail('');
      setHhNote('');
      setHeadName('');
      setHeadCccd('');
      setHeadPhone('');
      setHeadEmail('');
      setHeadDob('1990-01-01');
      setHeadGender('NAM');
    } catch (err: any) {
      toastError(err.message);
    }
  };

  // Handle Update Household
  const handleUpdateHousehold = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editHhTarget) return;
    try {
      await ApiClient.updateHousehold(editHhTarget.id, {
        contact_phone: editHhPhone.trim(),
        contact_email: editHhEmail.trim(),
        note: editHhNote.trim(),
      });
      success(`Đã cập nhật thông tin hộ gia đình ${editHhTarget.household_code} thành công!`);
      setEditHhOpen(false);
      setEditHhTarget(null);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const openChangeHeadModal = async (hh: Household) => {
    setChangeHeadTarget(hh);
    setNewHeadResidentId(hh.head_resident_id || '');
    setChangeHeadDate(new Date().toISOString().split('T')[0]);
    setChangeHeadReason('');
    setHeadCandidates([]);
    setChangeHeadOpen(true);

    setLoadingHeadCandidates(true);
    try {
      const res = await ApiClient.getHouseholdResidents(hh.id, { page: 1, page_size: 100 });
      const activeMembers = (res.items || []).filter(
        (r) =>
          !r.is_deleted &&
          (r.residence_status === 'THUONG_TRU' || r.residence_status === 'TAM_VANG')
      );
      setHeadCandidates(activeMembers);
      const nonHead = activeMembers.find((r) => !r.is_head);
      if (nonHead) {
        setNewHeadResidentId(nonHead.id);
      } else if (activeMembers.length > 0) {
        setNewHeadResidentId(activeMembers[0].id);
      }
    } catch (err: any) {
      toastError(err.message || 'Không thể tải danh sách nhân khẩu trong hộ.');
    } finally {
      setLoadingHeadCandidates(false);
    }
  };

  // Handle Change Household Head
  const handleChangeHead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!changeHeadTarget || !newHeadResidentId) {
      toastError('Vui lòng chọn nhân khẩu làm chủ hộ mới.');
      return;
    }
    try {
      await ApiClient.changeHead(changeHeadTarget.id, {
        new_head_resident_id: Number(newHeadResidentId),
        effective_date: changeHeadDate,
        reason: changeHeadReason.trim() || undefined,
      });
      success(`Đã thay đổi chủ hộ cho hộ ${changeHeadTarget.household_code} thành công!`);
      setChangeHeadOpen(false);
      setChangeHeadTarget(null);
      setNewHeadResidentId('');
      setChangeHeadReason('');
      loadData();
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
      success(`Chuyển nhượng căn hộ thành công! Hồ sơ cư trú mới đã có hiệu lực.`);
      setTransferOpen(false);
      setTransferSourceHh(null);
      setTransferTargetHhId('');
      setTransferReason('');
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const allActiveApartments = useMemo(
    () => allApartments.filter((a) => a.status === 'ACTIVE'),
    [allApartments]
  );

  // Filter across all loaded apartments when searching by code (GET /apartments has no q param)
  const aptSearchClean = aptSearch.trim().toLowerCase();
  const matchingApartments = useMemo(() => {
    if (!aptSearchClean) return apartments;
    const source = allApartmentsLoaded ? allApartments : apartments;
    return source.filter((apt) => {
      if (!apt.code.toLowerCase().includes(aptSearchClean)) return false;
      if (allApartmentsLoaded) {
        if (aptFloorFilter !== 'ALL' && apt.floor !== Number(aptFloorFilter)) return false;
        if (aptStatusFilter !== 'ALL' && apt.status !== aptStatusFilter) return false;
      }
      return true;
    });
  }, [aptSearchClean, apartments, allApartmentsLoaded, allApartments, aptFloorFilter, aptStatusFilter]);

  const isClientAptSearching = Boolean(aptSearchClean && allApartmentsLoaded);
  const displayedAptTotal = isClientAptSearching ? matchingApartments.length : aptTotal;
  const aptTotalPages = Math.max(1, Math.ceil(displayedAptTotal / PAGE_SIZE));
  const filteredApartments = isClientAptSearching
    ? matchingApartments.slice((aptPage - 1) * PAGE_SIZE, aptPage * PAGE_SIZE)
    : matchingApartments;

  const availableFloors = useMemo(
    () =>
      Array.from(new Set([...apartments, ...allApartments].map((a) => a.floor))).sort(
        (a, b) => a - b
      ),
    [apartments, allApartments]
  );

  // Occupied apartment IDs from active households
  const occupiedAptIds = new Set(
    allActiveHouseholds.map((h) => h.apartment_id).filter((id): id is number => Boolean(id))
  );

  // Target households that have no apartment yet
  const availableTargetHouseholds = allActiveHouseholds.filter(
    (h) =>
      h.id !== transferSourceHh?.id &&
      h.status === 'ACTIVE' &&
      !h.apartment_code &&
      !h.apartment_id
  );

  const hhTotalPages = Math.max(1, Math.ceil(hhTotal / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Building2 className="w-6 h-6 text-blue-600" />
            <span>Quản lý Căn hộ & Hộ gia đình</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Quản lý danh sách căn hộ vật lý, hộ gia đình cư trú, chuyển nhượng và bàn giao căn hộ.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            isLoading={loading}
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
                Nhập Excel
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
            </>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Không thể tải dữ liệu</p>
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
          onClick={() => {
            setActiveTab('apartments');
            setSearchParams({ tab: 'apartments' });
          }}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'apartments'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Home className="w-4 h-4" />
          <span>Danh sách Căn hộ ({aptTotal})</span>
        </button>

        <button
          onClick={() => {
            setActiveTab('households');
            setSearchParams({ tab: 'households' });
          }}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition ${
            activeTab === 'households'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Danh sách Hộ gia đình ({hhTotal})</span>
        </button>
      </div>

      {/* TAB 1: APARTMENTS */}
      {activeTab === 'apartments' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
            <Input
              placeholder="Tìm theo mã căn hộ (VD: P.1001)..."
              value={aptSearch}
              onChange={(e) => {
                setAptSearch(e.target.value);
                setAptPage(1);
              }}
              icon={<Search className="w-4 h-4" />}
            />

            <div>
              <select
                value={aptFloorFilter}
                onChange={(e) => {
                  setAptFloorFilter(e.target.value);
                  setAptPage(1);
                }}
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
                onChange={(e) => {
                  setAptStatusFilter(e.target.value);
                  setAptPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả trạng thái</option>
                <option value="ACTIVE">Hoạt động</option>
                <option value="INACTIVE">Tạm khóa</option>
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
                    {isAdmin && <th className="py-3 px-4 text-right">Thao tác</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredApartments.length === 0 ? (
                    <tr>
                      <td colSpan={isAdmin ? 6 : 5} className="py-8 text-center text-slate-400">
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
                        {isAdmin && (
                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={() => {
                                setSelectedApt(apt);
                                setEditFloor(apt.floor);
                                setEditArea(String(apt.area_m2));
                                setEditStatus(apt.status);
                                setEditNote(apt.note || '');
                                setEditAptOpen(true);
                              }}
                              className="text-xs font-semibold text-blue-600 hover:text-blue-800 p-1 rounded transition"
                            >
                              Chỉnh sửa
                            </button>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
              <span>
                Trang {aptPage} / {aptTotalPages} (Tổng {displayedAptTotal} căn hộ)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={aptPage <= 1 || loading}
                  onClick={() => setAptPage((p) => Math.max(1, p - 1))}
                >
                  Trang trước
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={aptPage >= aptTotalPages || loading}
                  onClick={() => setAptPage((p) => Math.min(aptTotalPages, p + 1))}
                >
                  Trang sau
                </Button>
              </div>
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
              placeholder="Tìm theo mã hộ, tên chủ hộ, SĐT..."
              value={hhSearch}
              onChange={(e) => setHhSearch(e.target.value)}
              icon={<Search className="w-4 h-4" />}
            />

            <div>
              <select
                value={hhStatusFilter}
                onChange={(e) => {
                  setHhStatusFilter(e.target.value);
                  setHhPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả trạng thái</option>
                <option value="ACTIVE">Đang cư trú</option>
                <option value="INACTIVE">Đã ngừng quản lý</option>
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
                    <th className="py-3 px-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {households.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        {loading ? 'Đang tải danh sách hộ gia đình...' : 'Không có hộ gia đình nào phù hợp.'}
                      </td>
                    </tr>
                  ) : (
                    households.map((hh) => (
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
                          <div className="flex items-center justify-end gap-1.5 flex-wrap">
                            <Link
                              to={`/residents?household_id=${hh.id}`}
                              className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-900 px-2 py-1 rounded hover:bg-emerald-50 transition"
                              title="Xem và quản lý nhân khẩu của hộ"
                            >
                              Nhân khẩu
                            </Link>
                            {isAdmin && hh.status === 'ACTIVE' && (
                              <>
                                <button
                                  onClick={() => {
                                    setEditHhTarget(hh);
                                    setEditHhPhone(hh.contact_phone || '');
                                    setEditHhEmail(hh.contact_email || '');
                                    setEditHhNote(hh.note || '');
                                    setEditHhOpen(true);
                                  }}
                                  className="text-[11px] font-semibold text-slate-700 hover:text-blue-600 px-2 py-1 rounded hover:bg-slate-100 transition"
                                  title="Chỉnh sửa thông tin liên hệ hộ gia đình"
                                >
                                  Sửa
                                </button>
                                <button
                                  onClick={() => openChangeHeadModal(hh)}
                                  className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded hover:bg-indigo-50 transition"
                                  title="Thay đổi chủ hộ đại diện"
                                >
                                  Đổi chủ hộ
                                </button>
                                <button
                                  onClick={() => {
                                    setTransferSourceHh(hh);
                                    setTransferTargetHhId('');
                                    setTransferOpen(true);
                                  }}
                                  className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50 transition"
                                  title="Chuyển nhượng căn hộ sang hộ khác"
                                >
                                  Chuyển nhượng
                                </button>
                                <button
                                  onClick={() => {
                                    setTargetHh(hh);
                                    setDeactivateOpen(true);
                                  }}
                                  className="text-[11px] font-semibold text-rose-600 hover:text-rose-800 px-2 py-1 rounded hover:bg-rose-50 transition"
                                  title="Ngừng quản lý hộ gia đình"
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

            <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
              <span>
                Trang {hhPage} / {hhTotalPages} (Tổng {hhTotal} hộ gia đình)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={hhPage <= 1 || loading}
                  onClick={() => setHhPage((p) => Math.max(1, p - 1))}
                >
                  Trang trước
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={hhPage >= hhTotalPages || loading}
                  onClick={() => setHhPage((p) => Math.min(hhTotalPages, p + 1))}
                >
                  Trang sau
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Thêm căn hộ mới */}
      <Modal
        isOpen={addAptOpen}
        onClose={() => setAddAptOpen(false)}
        title="Khai báo căn hộ mới"
        description="Đăng ký mã căn hộ và diện tích thực tế vào hệ thống."
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
              step="any"
              min="0.1"
              value={aptArea}
              onChange={(e) => setAptArea(e.target.value)}
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
              step="any"
              min="0.1"
              value={editArea}
              onChange={(e) => setEditArea(e.target.value)}
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
              <option value="ACTIVE">Hoạt động</option>
              <option value="INACTIVE">Tạm khóa</option>
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
        title="Khai báo hộ gia đình mới"
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
                {allActiveApartments
                  .filter((a) => !occupiedAptIds.has(a.id))
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} (Tầng {a.floor} - {a.area_m2}m²)
                    </option>
                  ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="SĐT liên hệ hộ"
              placeholder="0912345678"
              value={hhPhone}
              onChange={(e) => setHhPhone(e.target.value)}
            />
            <Input
              label="Email liên hệ hộ"
              type="email"
              placeholder="hogiadinh@bluemoon.local"
              value={hhEmail}
              onChange={(e) => setHhEmail(e.target.value)}
            />
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

            <Input
              label="Email chủ hộ"
              type="email"
              placeholder="chuho@bluemoon.local"
              value={headEmail}
              onChange={(e) => setHeadEmail(e.target.value)}
            />
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

      {/* Modal: Chỉnh sửa thông tin hộ gia đình */}
      <Modal
        isOpen={editHhOpen}
        onClose={() => setEditHhOpen(false)}
        title={`Chỉnh sửa thông tin hộ ${editHhTarget?.household_code}`}
        description="Cập nhật thông tin liên hệ và ghi chú của hộ gia đình."
      >
        <form onSubmit={handleUpdateHousehold} className="space-y-4">
          <Input
            label="Số điện thoại liên hệ"
            placeholder="Ví dụ: 0912345678"
            value={editHhPhone}
            onChange={(e) => setEditHhPhone(e.target.value)}
          />

          <Input
            label="Email liên hệ"
            type="email"
            placeholder="Ví dụ: contact@bluemoon.local"
            value={editHhEmail}
            onChange={(e) => setEditHhEmail(e.target.value)}
          />

          <Input
            label="Ghi chú"
            placeholder="Ghi chú về hộ gia đình..."
            value={editHhNote}
            onChange={(e) => setEditHhNote(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setEditHhOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu thay đổi
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Đổi chủ hộ */}
      <Modal
        isOpen={changeHeadOpen}
        onClose={() => setChangeHeadOpen(false)}
        title={`Thay đổi chủ hộ đại diện - Hộ ${changeHeadTarget?.household_code}`}
        description="Chọn một nhân khẩu hiện đang cư trú trong hộ để chỉ định làm chủ hộ mới."
      >
        <form onSubmit={handleChangeHead} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Nhân khẩu chủ hộ mới <span className="text-rose-500">*</span>
            </label>
            <select
              value={newHeadResidentId}
              onChange={(e) =>
                setNewHeadResidentId(e.target.value ? Number(e.target.value) : '')
              }
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
              disabled={loadingHeadCandidates}
            >
              <option value="">
                {loadingHeadCandidates
                  ? 'Đang tải danh sách nhân khẩu...'
                  : '-- Chọn nhân khẩu trong hộ --'}
              </option>
              {headCandidates.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.full_name} ({r.relationship_to_head || 'Thành viên'}
                  {r.is_head ? ' - Chủ hộ hiện tại' : ''})
                </option>
              ))}
            </select>
            {!loadingHeadCandidates && headCandidates.length === 0 && (
              <p className="text-[11px] text-amber-700 mt-1">
                Hộ chưa có nhân khẩu nào. Hãy thêm nhân khẩu trước khi chỉ định chủ hộ.
              </p>
            )}
          </div>

          <Input
            label="Ngày có hiệu lực"
            type="date"
            value={changeHeadDate}
            onChange={(e) => setChangeHeadDate(e.target.value)}
            required
          />

          <Input
            label="Lý do thay đổi chủ hộ"
            placeholder="Ví dụ: Thay đổi chủ hộ theo thỏa thuận gia đình..."
            value={changeHeadReason}
            onChange={(e) => setChangeHeadReason(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setChangeHeadOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit" disabled={!newHeadResidentId}>
              Xác nhận đổi chủ hộ
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Kết quả tạo hộ & Tài khoản Cư dân */}
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
                  Căn hộ: {createdHhResult.apartment_code || 'Chưa gán'} • Chủ hộ:{' '}
                  {createdHhResult.head_name || 'Chưa có'}
                </p>
              </div>
            </div>

            {createdHhResult.resident_account && (
              <div className="p-4 bg-slate-900 text-white rounded-2xl space-y-2 text-xs">
                <p className="font-bold text-amber-400 uppercase tracking-wider text-[11px]">
                  Tài khoản Cư dân khởi tạo tự động:
                </p>
                <div className="flex justify-between items-center py-1 border-b border-slate-800">
                  <span className="text-slate-400">Tên đăng nhập:</span>
                  <span className="font-mono font-bold text-white">
                    {createdHhResult.resident_account.username}
                  </span>
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

      {/* Modal: Chuyển nhượng căn hộ */}
      <Modal
        isOpen={transferOpen}
        onClose={() => setTransferOpen(false)}
        title="Chuyển nhượng quyền cư trú căn hộ"
        description={`Chuyển nhượng căn hộ ${transferSourceHh?.apartment_code || ''} từ hộ ${transferSourceHh?.household_code || ''} sang hộ mới.`}
      >
        <form onSubmit={handleTransfer} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Hộ gia đình nhận chuyển nhượng <span className="text-rose-500">*</span>
            </label>
            <select
              value={transferTargetHhId}
              onChange={(e) =>
                setTransferTargetHhId(e.target.value ? Number(e.target.value) : '')
              }
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              <option value="">-- Chọn hộ gia đình mới (chưa có căn hộ) --</option>
              {availableTargetHouseholds.length === 0 ? (
                <option value="" disabled>
                  Không có hộ gia đình nào chưa có căn hộ
                </option>
              ) : (
                availableTargetHouseholds.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.household_code} - {h.head_name || 'Chưa rõ chủ hộ'}
                  </option>
                ))
              )}
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

      {/* Modal: Ngừng quản lý hộ gia đình */}
      <Modal
        isOpen={deactivateOpen}
        onClose={() => setDeactivateOpen(false)}
        title="Ngừng quản lý hộ gia đình"
        description={`Bạn có chắc muốn chuyển trạng thái hộ ${targetHh?.household_code || ''} sang ngừng hoạt động?`}
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

      {/* Modal: Import Excel */}
      {isAdmin && (
        <ExcelImportModal
          isOpen={importOpen}
          onClose={() => setImportOpen(false)}
          onSuccess={loadData}
        />
      )}
    </div>
  );
};
