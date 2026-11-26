import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Car,
  Plus,
  RefreshCw,
  AlertCircle,
  Search,
  Pencil,
  Ban,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { ApiClient } from '../../api';
import { Household, Vehicle, VehicleType } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 20;

export const VehiclesPage: React.FC = () => {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('ADMIN');
  const { success, error: toastError } = useToast();
  const [searchParams] = useSearchParams();

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters matching GET /api/v1/vehicles
  const [plateSearch, setPlateSearch] = useState(() => searchParams.get('q') || '');
  const [debouncedPlate, setDebouncedPlate] = useState(() => searchParams.get('q') || '');
  const [householdFilter, setHouseholdFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Register Vehicle Modal
  const [addOpen, setAddOpen] = useState(false);
  const [newHouseholdId, setNewHouseholdId] = useState<number | ''>('');
  const [newPlateNumber, setNewPlateNumber] = useState('');
  const [newVehicleType, setNewVehicleType] = useState<VehicleType>('MOTORBIKE');
  const [newBrand, setNewBrand] = useState('');
  const [newColor, setNewColor] = useState('');
  const [newRegisteredDate, setNewRegisteredDate] = useState(
    () => new Date().toISOString().split('T')[0]
  );

  // Edit Vehicle Modal
  const [editOpen, setEditOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Vehicle | null>(null);
  const [editPlateNumber, setEditPlateNumber] = useState('');
  const [editVehicleType, setEditVehicleType] = useState<VehicleType>('MOTORBIKE');
  const [editBrand, setEditBrand] = useState('');
  const [editColor, setEditColor] = useState('');

  // Unregister Modal
  const [unregisterTarget, setUnregisterTarget] = useState<Vehicle | null>(null);
  const [unregisterDate, setUnregisterDate] = useState(
    () => new Date().toISOString().split('T')[0]
  );

  useEffect(() => {
    const qParam = searchParams.get('q');
    if (qParam !== null) {
      setPlateSearch(qParam);
      setDebouncedPlate(qParam);
      setPage(1);
    }
  }, [searchParams]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedPlate(plateSearch.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [plateSearch]);

  const loadHouseholds = useCallback(async () => {
    try {
      const items = await ApiClient.fetchAllPages((page, pageSize) =>
        ApiClient.getHouseholds({ page, page_size: pageSize })
      );
      setHouseholds(items);
    } catch {
      // Handled gracefully if offline
    }
  }, []);

  const loadVehicles = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await ApiClient.getVehicles({
        page,
        page_size: PAGE_SIZE,
        household_id: householdFilter !== 'ALL' ? Number(householdFilter) : undefined,
        plate_number: debouncedPlate || undefined,
        vehicle_type: typeFilter !== 'ALL' ? typeFilter : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
      });
      setVehicles(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách phương tiện từ máy chủ.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [page, householdFilter, debouncedPlate, typeFilter, statusFilter, toastError]);

  useEffect(() => {
    loadHouseholds();
  }, [loadHouseholds]);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  const householdMap = useMemo(() => {
    const map = new Map<number, Household>();
    households.forEach((h) => map.set(h.id, h));
    return map;
  }, [households]);

  const activeHouseholds = useMemo(
    () => households.filter((h) => h.status === 'ACTIVE'),
    [households]
  );

  const handleAddVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHouseholdId) {
      toastError('Vui lòng chọn hộ gia đình sở hữu phương tiện.');
      return;
    }
    try {
      await ApiClient.createVehicle({
        household_id: Number(newHouseholdId),
        plate_number: newPlateNumber.trim().toUpperCase(),
        vehicle_type: newVehicleType,
        brand: newBrand.trim() || undefined,
        color: newColor.trim() || undefined,
        registered_date: newRegisteredDate || undefined,
      });
      success(`Đã đăng ký phương tiện biển số ${newPlateNumber.trim().toUpperCase()}!`);
      setAddOpen(false);
      setNewPlateNumber('');
      setNewBrand('');
      setNewColor('');
      loadVehicles();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleEditVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;
    try {
      await ApiClient.updateVehicle(editTarget.id, {
        plate_number: editPlateNumber.trim().toUpperCase(),
        vehicle_type: editVehicleType,
        brand: editBrand.trim(),
        color: editColor.trim(),
      });
      success(`Đã cập nhật thông tin phương tiện ${editPlateNumber.trim().toUpperCase()}!`);
      setEditOpen(false);
      setEditTarget(null);
      loadVehicles();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleUnregister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!unregisterTarget) return;
    try {
      await ApiClient.unregisterVehicle(unregisterTarget.id, {
        unregistered_date: unregisterDate || undefined,
      });
      success(`Đã hủy đăng ký gửi xe ${unregisterTarget.plate_number}.`);
      setUnregisterTarget(null);
      loadVehicles();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const getVehicleTypeLabel = (t: VehicleType) => {
    switch (t) {
      case 'MOTORBIKE':
        return 'Xe máy';
      case 'CAR':
        return 'Ô tô';
      case 'BICYCLE':
        return 'Xe đạp / Xe điện';
      default:
        return t;
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Car className="w-6 h-6 text-blue-600" />
            <span>Quản lý Phương tiện Gửi xe</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Theo dõi thẻ xe máy, ô tô, xe đạp theo từng hộ gia đình làm căn cứ tính phí trông giữ xe hàng tháng.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadVehicles}
            isLoading={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
          {isAdmin && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setNewRegisteredDate(new Date().toISOString().split('T')[0]);
                setAddOpen(true);
              }}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              Đăng ký xe mới
            </Button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Không thể tải dữ liệu phương tiện</p>
              <p className="text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={loadVehicles}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
        <Input
          placeholder="Tìm theo biển số xe (VD: 29A-12345)..."
          value={plateSearch}
          onChange={(e) => setPlateSearch(e.target.value)}
          icon={<Search className="w-4 h-4" />}
        />

        <div>
          <select
            value={householdFilter}
            onChange={(e) => {
              setHouseholdFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả hộ gia đình</option>
            {households.map((h) => (
              <option key={h.id} value={String(h.id)}>
                {h.household_code} {h.apartment_code ? `(${h.apartment_code})` : ''} -{' '}
                {h.head_name || 'Chưa rõ chủ hộ'}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả loại xe</option>
            <option value="MOTORBIKE">Xe máy</option>
            <option value="CAR">Ô tô</option>
            <option value="BICYCLE">Xe đạp / Xe điện</option>
          </select>
        </div>

        <div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả trạng thái</option>
            <option value="ACTIVE">Đang gửi xe</option>
            <option value="INACTIVE">Đã hủy đăng ký</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh sách phương tiện</h3>
          <span className="text-xs text-slate-500 font-mono">Tổng số: {total} xe</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Biển số</th>
                <th className="py-3 px-4">Loại phương tiện</th>
                <th className="py-3 px-4">Hộ gia đình / Căn hộ</th>
                <th className="py-3 px-4">Hãng / Màu sắc</th>
                <th className="py-3 px-4">Ngày đăng ký</th>
                <th className="py-3 px-4">Ngày hủy</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                {isAdmin && <th className="py-3 px-4 text-right">Thao tác</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {vehicles.length === 0 ? (
                <tr>
                  <td colSpan={isAdmin ? 8 : 7} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải danh sách phương tiện...' : 'Không tìm thấy phương tiện phù hợp.'}
                  </td>
                </tr>
              ) : (
                vehicles.map((v) => {
                  const hh = householdMap.get(v.household_id);
                  return (
                    <tr key={v.id} className="hover:bg-slate-50">
                      <td className="py-3.5 px-4 font-mono font-bold text-blue-700">
                        {v.plate_number}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-800">
                        {getVehicleTypeLabel(v.vehicle_type)}
                      </td>
                      <td className="py-3.5 px-4">
                        {hh ? (
                          <div>
                            <span className="font-mono font-semibold text-slate-800">
                              {hh.household_code}
                            </span>
                            {hh.apartment_code && (
                              <span className="ml-1.5 bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono text-[11px]">
                                {hh.apartment_code}
                              </span>
                            )}
                            {hh.head_name && (
                              <p className="text-[11px] text-slate-500">{hh.head_name}</p>
                            )}
                          </div>
                        ) : (
                          <span className="font-mono text-slate-600">Hộ #{v.household_id}</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        {v.brand || v.color
                          ? `${v.brand || '---'} / ${v.color || '---'}`
                          : '---'}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">{v.registered_date}</td>
                      <td className="py-3.5 px-4 font-mono text-slate-500">
                        {v.unregistered_date || '---'}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <Badge
                          variant={v.status === 'ACTIVE' ? 'success' : 'neutral'}
                          dot
                          size="sm"
                        >
                          {v.status === 'ACTIVE' ? 'Đang gửi' : 'Đã hủy'}
                        </Badge>
                      </td>
                      {isAdmin && (
                        <td className="py-3.5 px-4 text-right">
                          {v.status === 'ACTIVE' && (
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => {
                                  setEditTarget(v);
                                  setEditPlateNumber(v.plate_number);
                                  setEditVehicleType(v.vehicle_type);
                                  setEditBrand(v.brand || '');
                                  setEditColor(v.color || '');
                                  setEditOpen(true);
                                }}
                                className="p-1.5 rounded-lg text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition"
                                title="Chỉnh sửa thông tin xe"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => {
                                  setUnregisterTarget(v);
                                  setUnregisterDate(new Date().toISOString().split('T')[0]);
                                }}
                                className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 transition"
                                title="Hủy đăng ký gửi xe"
                              >
                                <Ban className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
          <span>
            Trang {page} / {totalPages}
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

      {/* Modal: Đăng ký xe mới */}
      <Modal
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        title="Đăng ký phương tiện gửi xe mới"
        description="Gắn phương tiện cho hộ gia đình để tự động tính phí giữ xe hàng tháng."
      >
        <form onSubmit={handleAddVehicle} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Hộ gia đình <span className="text-rose-500">*</span>
            </label>
            <select
              value={newHouseholdId}
              onChange={(e) =>
                setNewHouseholdId(e.target.value ? Number(e.target.value) : '')
              }
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              <option value="">-- Chọn hộ gia đình --</option>
              {activeHouseholds.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.household_code} {h.apartment_code ? `(${h.apartment_code})` : ''} -{' '}
                  {h.head_name || 'Chưa rõ chủ hộ'}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Biển số xe"
              placeholder="Ví dụ: 29A-123.45"
              value={newPlateNumber}
              onChange={(e) => setNewPlateNumber(e.target.value.toUpperCase())}
              required
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Loại phương tiện <span className="text-rose-500">*</span>
              </label>
              <select
                value={newVehicleType}
                onChange={(e) => setNewVehicleType(e.target.value as VehicleType)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="MOTORBIKE">Xe máy</option>
                <option value="CAR">Ô tô</option>
                <option value="BICYCLE">Xe đạp / Xe điện</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Hãng xe"
              placeholder="Honda, Toyota..."
              value={newBrand}
              onChange={(e) => setNewBrand(e.target.value)}
            />
            <Input
              label="Màu sắc"
              placeholder="Đen, Trắng..."
              value={newColor}
              onChange={(e) => setNewColor(e.target.value)}
            />
          </div>

          <Input
            label="Ngày đăng ký gửi xe"
            type="date"
            value={newRegisteredDate}
            onChange={(e) => setNewRegisteredDate(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Xác nhận đăng ký
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Chỉnh sửa phương tiện */}
      <Modal
        isOpen={editOpen}
        onClose={() => setEditOpen(false)}
        title={`Cập nhật phương tiện ${editTarget?.plate_number || ''}`}
        description="Chỉnh sửa biển số, loại phương tiện, hãng hoặc màu sắc."
      >
        <form onSubmit={handleEditVehicle} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Biển số xe"
              value={editPlateNumber}
              onChange={(e) => setEditPlateNumber(e.target.value.toUpperCase())}
              required
            />
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Loại phương tiện <span className="text-rose-500">*</span>
              </label>
              <select
                value={editVehicleType}
                onChange={(e) => setEditVehicleType(e.target.value as VehicleType)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="MOTORBIKE">Xe máy</option>
                <option value="CAR">Ô tô</option>
                <option value="BICYCLE">Xe đạp / Xe điện</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Hãng xe"
              value={editBrand}
              onChange={(e) => setEditBrand(e.target.value)}
            />
            <Input
              label="Màu sắc"
              value={editColor}
              onChange={(e) => setEditColor(e.target.value)}
            />
          </div>

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

      {/* Modal: Hủy đăng ký phương tiện */}
      {unregisterTarget && (
        <Modal
          isOpen={true}
          onClose={() => setUnregisterTarget(null)}
          title="Hủy đăng ký gửi xe"
          description={`Phương tiện ${unregisterTarget.plate_number} sẽ ngừng tính phí từ ngày hủy đăng ký.`}
        >
          <form onSubmit={handleUnregister} className="space-y-4">
            <Input
              label="Ngày hủy đăng ký"
              type="date"
              min={unregisterTarget.registered_date}
              value={unregisterDate}
              onChange={(e) => setUnregisterDate(e.target.value)}
              helperText={`Phải từ ngày đăng ký (${unregisterTarget.registered_date}) trở đi.`}
            />

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button
                variant="outline"
                type="button"
                onClick={() => setUnregisterTarget(null)}
              >
                Hủy
              </Button>
              <Button variant="danger" type="submit">
                Xác nhận hủy đăng ký
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
