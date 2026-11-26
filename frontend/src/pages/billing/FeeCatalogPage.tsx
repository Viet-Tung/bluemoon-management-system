import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  Plus,
  RefreshCw,
  AlertCircle,
  Search,
  History,
  BadgePercent,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { ApiClient } from '../../api';
import { FeeType, FeeRate, FeeGroup, CalcMethod, FeeCycle } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 50;

export const FeeCatalogPage: React.FC = () => {
  const { success, error: toastError } = useToast();
  const [feeTypes, setFeeTypes] = useState<FeeType[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [searchKw, setSearchKw] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [groupFilter, setGroupFilter] = useState<string>('ALL');

  // Add Fee Modal
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [feeGroup, setFeeGroup] = useState<FeeGroup>('MANAGEMENT');
  const [calcMethod, setCalcMethod] = useState<CalcMethod>('PER_M2');
  const [unitLabel, setUnitLabel] = useState('m²');
  const [vehicleType, setVehicleType] = useState<string>('MOTORBIKE');
  const [isPassThrough, setIsPassThrough] = useState(false);
  const [cycle, setCycle] = useState<FeeCycle>('MONTHLY');
  const [dueDay, setDueDay] = useState<number>(15);
  const [description, setDescription] = useState('');

  // Edit Fee Modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedFee, setSelectedFee] = useState<FeeType | null>(null);
  const [editName, setEditName] = useState('');
  const [editUnitLabel, setEditUnitLabel] = useState('');
  const [editCycle, setEditCycle] = useState<FeeCycle>('MONTHLY');
  const [editDueDay, setEditDueDay] = useState<number>(15);
  const [editDescription, setEditDescription] = useState('');

  // Fee Rates Modal (US-14)
  const [ratesModalOpen, setRatesModalOpen] = useState(false);
  const [ratesTargetFee, setRatesTargetFee] = useState<FeeType | null>(null);
  const [ratesList, setRatesList] = useState<FeeRate[]>([]);
  const [loadingRates, setLoadingRates] = useState(false);
  const [newUnitPrice, setNewUnitPrice] = useState('');
  const [newEffectiveFrom, setNewEffectiveFrom] = useState(
    () => new Date().toISOString().split('T')[0]
  );
  const [submittingRate, setSubmittingRate] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const params: any = { page, page_size: PAGE_SIZE };
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (groupFilter !== 'ALL') params.fee_group = groupFilter;

      const data = await ApiClient.getFeeTypes(params);
      setFeeTypes(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh mục khoản thu từ máy chủ.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, groupFilter, toastError]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAddFee = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        code: code.trim().toUpperCase(),
        name: name.trim(),
        fee_group: feeGroup,
        calc_method: calcMethod,
        unit_label: unitLabel.trim(),
        is_pass_through: isPassThrough,
        cycle,
        due_day: Number(dueDay),
        description: description.trim() || undefined,
      };

      if (calcMethod === 'PER_VEHICLE') {
        payload.vehicle_type = vehicleType;
      }

      await ApiClient.createFeeType(payload);
      success(`Đã thêm khoản thu ${name.trim()} thành công!`);
      setAddModalOpen(false);
      setCode('');
      setName('');
      setDescription('');
      setIsPassThrough(false);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleUpdateFee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFee) return;
    try {
      await ApiClient.updateFeeType(selectedFee.id, {
        name: editName.trim(),
        unit_label: editUnitLabel.trim(),
        cycle: editCycle,
        due_day: Number(editDueDay),
        description: editDescription.trim(),
      });
      success(`Đã cập nhật khoản thu "${editName.trim()}" thành công!`);
      setEditModalOpen(false);
      setSelectedFee(null);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleDeactivate = async (id: number, feeName: string) => {
    if (
      !window.confirm(
        `Bạn có chắc muốn ngừng áp dụng khoản thu "${feeName}"? (Dữ liệu lịch sử vẫn được giữ nguyên)`
      )
    ) {
      return;
    }
    try {
      await ApiClient.deactivateFeeType(id);
      success(`Đã ngừng áp dụng khoản thu "${feeName}".`);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const openRatesModal = async (fee: FeeType) => {
    setRatesTargetFee(fee);
    setRatesList([]);
    setNewUnitPrice(
      fee.current_unit_price !== null && fee.current_unit_price !== undefined
        ? String(fee.current_unit_price)
        : ''
    );
    setNewEffectiveFrom(new Date().toISOString().split('T')[0]);
    setRatesModalOpen(true);
    setLoadingRates(true);
    try {
      const [freshFee, rates] = await Promise.all([
        ApiClient.getFeeType(fee.id),
        ApiClient.getFeeRates(fee.id),
      ]);
      setRatesTargetFee(freshFee);
      setRatesList(rates || []);
    } catch (err: any) {
      toastError(err.message || 'Không thể tải lịch sử đơn giá.');
    } finally {
      setLoadingRates(false);
    }
  };

  const handleCreateRate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ratesTargetFee) return;
    const price = Number(newUnitPrice);
    if (newUnitPrice.trim() === '' || isNaN(price) || !Number.isInteger(price) || price < 0) {
      toastError('Đơn giá phải là số nguyên không âm (VNĐ).');
      return;
    }
    setSubmittingRate(true);
    try {
      await ApiClient.createFeeRate(ratesTargetFee.id, {
        unit_price: price,
        effective_from: newEffectiveFrom,
      });
      success(`Đã thiết lập đơn giá ${formatVND(price)} từ ${newEffectiveFrom}!`);
      const [freshFee, rates] = await Promise.all([
        ApiClient.getFeeType(ratesTargetFee.id),
        ApiClient.getFeeRates(ratesTargetFee.id),
      ]);
      setRatesTargetFee(freshFee);
      setRatesList(rates || []);
      loadData();
    } catch (err: any) {
      toastError(err.message);
    } finally {
      setSubmittingRate(false);
    }
  };

  const formatVND = (num?: number | null) => {
    if (num === null || num === undefined) return 'Chưa thiết lập';
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  const getGroupName = (g: FeeGroup) => {
    switch (g) {
      case 'MANAGEMENT':
        return 'Quản lý vận hành';
      case 'PARKING':
        return 'Trông giữ xe';
      case 'UTILITY':
        return 'Điện / Nước / Dịch vụ';
      case 'OTHER':
        return 'Khoản thu khác';
      default:
        return g;
    }
  };

  const getCalcMethodName = (m: CalcMethod) => {
    switch (m) {
      case 'PER_M2':
        return 'Theo diện tích sàn (m²)';
      case 'PER_HOUSEHOLD':
        return 'Cố định theo hộ';
      case 'PER_PERSON':
        return 'Theo số nhân khẩu';
      case 'PER_VEHICLE':
        return 'Theo số lượng xe';
      case 'METERED':
        return 'Theo chỉ số công tơ';
      default:
        return m;
    }
  };

  const getCycleLabel = (c: FeeCycle) => {
    switch (c) {
      case 'MONTHLY':
        return 'Hàng tháng';
      case 'QUARTERLY':
        return 'Hàng quý';
      case 'YEARLY':
        return 'Hàng năm';
      default:
        return c;
    }
  };

  const filteredFeeTypes = feeTypes.filter((f) => {
    const q = searchKw.trim().toLowerCase();
    if (!q) return true;
    return (
      f.code.toLowerCase().includes(q) ||
      f.name.toLowerCase().includes(q) ||
      (f.description && f.description.toLowerCase().includes(q))
    );
  });

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-600" />
            <span>Danh mục Khoản thu & Biểu phí</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Cấu hình các khoản thu bắt buộc, đơn giá theo từng thời kỳ hiệu lực và hạn nộp hàng tháng.
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
          <Link to="/fee-exemptions">
            <Button
              variant="secondary"
              size="sm"
              icon={<BadgePercent className="w-3.5 h-3.5 text-indigo-600" />}
            >
              Chính sách miễn giảm
            </Button>
          </Link>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setAddModalOpen(true)}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Tạo khoản thu mới
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Không thể tải dữ liệu khoản thu</p>
              <p className="text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={loadData}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Tìm kiếm</label>
          <Input
            placeholder="Tìm theo tên hoặc mã phí..."
            value={searchKw}
            onChange={(e) => setSearchKw(e.target.value)}
            icon={<Search className="w-4 h-4" />}
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Nhóm khoản thu</label>
          <select
            value={groupFilter}
            onChange={(e) => {
              setGroupFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả các nhóm phí</option>
            <option value="MANAGEMENT">Quản lý vận hành</option>
            <option value="PARKING">Trông giữ xe</option>
            <option value="UTILITY">Điện / Nước / Dịch vụ</option>
            <option value="OTHER">Khoản thu khác</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Trạng thái áp dụng</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả trạng thái</option>
            <option value="ACTIVE">Đang áp dụng</option>
            <option value="INACTIVE">Đã ngừng áp dụng</option>
          </select>
        </div>
      </div>

      {/* Fee Catalog Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh mục khoản thu trong hệ thống</h3>
          <span className="text-xs text-slate-500 font-mono">Tổng số: {total} loại phí</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Mã Phí</th>
                <th className="py-3 px-4">Tên khoản thu</th>
                <th className="py-3 px-4">Nhóm phí</th>
                <th className="py-3 px-4">Phương pháp tính</th>
                <th className="py-3 px-4">Đơn vị tính</th>
                <th className="py-3 px-4">Đơn giá hiện hành</th>
                <th className="py-3 px-4">Kỳ tính / Hạn nộp</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredFeeTypes.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải danh mục khoản thu...' : 'Không có khoản thu nào phù hợp.'}
                  </td>
                </tr>
              ) : (
                filteredFeeTypes.map((fee) => (
                  <tr key={fee.id} className="hover:bg-slate-50">
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-700">{fee.code}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      <div className="flex items-center gap-1.5">
                        <span>{fee.name}</span>
                        {fee.is_pass_through && (
                          <Badge variant="warning" size="sm">
                            Thu hộ
                          </Badge>
                        )}
                      </div>
                      {fee.description && (
                        <div className="text-[11px] text-slate-400 font-normal">{fee.description}</div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-700 font-medium">
                      {getGroupName(fee.fee_group)}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 font-medium">
                      {getCalcMethodName(fee.calc_method)}
                      {fee.vehicle_type && (
                        <span className="ml-1 text-[10px] text-blue-600 font-semibold font-mono">
                          ({fee.vehicle_type})
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">
                      {fee.unit_label}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-900 font-mono">
                      {formatVND(fee.current_unit_price)}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <span>{getCycleLabel(fee.cycle)}</span>
                      {fee.due_day && <span className="text-slate-400"> (Ngày {fee.due_day})</span>}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge variant={fee.status === 'ACTIVE' ? 'success' : 'danger'} dot size="sm">
                        {fee.status === 'ACTIVE' ? 'Đang dùng' : 'Đã ngừng'}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => openRatesModal(fee)}
                          className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded hover:bg-indigo-50 transition inline-flex items-center gap-1"
                          title="Xem lịch sử và cập nhật đơn giá"
                        >
                          <History className="w-3 h-3" />
                          <span>Đơn giá</span>
                        </button>
                        {fee.status === 'ACTIVE' && (
                          <>
                            <button
                              onClick={() => {
                                setSelectedFee(fee);
                                setEditName(fee.name);
                                setEditUnitLabel(fee.unit_label);
                                setEditCycle(fee.cycle);
                                setEditDueDay(fee.due_day || 15);
                                setEditDescription(fee.description || '');
                                setEditModalOpen(true);
                              }}
                              className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50 transition"
                              title="Chỉnh sửa thông tin khoản thu"
                            >
                              Chỉnh sửa
                            </button>
                            <button
                              onClick={() => handleDeactivate(fee.id, fee.name)}
                              className="text-[11px] font-semibold text-rose-600 hover:text-rose-800 px-2 py-1 rounded hover:bg-rose-50 transition"
                              title="Ngừng áp dụng khoản thu"
                            >
                              Ngừng áp dụng
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

        {totalPages > 1 && (
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
        )}
      </div>

      {/* Modal Add Fee Type */}
      <Modal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title="Tạo khoản thu bắt buộc mới"
        description="Đăng ký thêm loại phí áp dụng cho cư dân tòa nhà."
      >
        <form onSubmit={handleAddFee} className="space-y-4">
          <Input
            label="Mã khoản thu (Viết hoa, không dấu)"
            placeholder="Ví dụ: PQL, P_XE_MAY..."
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            required
          />
          <Input
            label="Tên khoản thu"
            placeholder="Ví dụ: Phí quản lý vận hành tòa nhà..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Nhóm khoản thu</label>
              <select
                value={feeGroup}
                onChange={(e) => setFeeGroup(e.target.value as any)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="MANAGEMENT">Quản lý vận hành</option>
                <option value="PARKING">Trông giữ xe</option>
                <option value="UTILITY">Điện / Nước / Dịch vụ</option>
                <option value="OTHER">Khoản thu khác</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Phương pháp tính</label>
              <select
                value={calcMethod}
                onChange={(e) => setCalcMethod(e.target.value as any)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="PER_M2">Theo diện tích sàn (m²)</option>
                <option value="PER_HOUSEHOLD">Cố định theo hộ</option>
                <option value="PER_PERSON">Theo số nhân khẩu</option>
                <option value="PER_VEHICLE">Theo số lượng xe</option>
                <option value="METERED">Theo chỉ số công tơ</option>
              </select>
            </div>
          </div>

          {calcMethod === 'PER_VEHICLE' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Loại phương tiện</label>
              <select
                value={vehicleType}
                onChange={(e) => setVehicleType(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="MOTORBIKE">Xe máy</option>
                <option value="CAR">Ô tô</option>
                <option value="BICYCLE">Xe đạp / Xe điện</option>
              </select>
            </div>
          )}

          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Đơn vị tính"
              placeholder="m², hộ, xe, kWh..."
              value={unitLabel}
              onChange={(e) => setUnitLabel(e.target.value)}
              required
            />
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Chu kỳ thu</label>
              <select
                value={cycle}
                onChange={(e) => setCycle(e.target.value as FeeCycle)}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="MONTHLY">Hàng tháng</option>
                <option value="QUARTERLY">Hàng quý</option>
                <option value="YEARLY">Hàng năm</option>
              </select>
            </div>
            <Input
              label="Ngày hạn nộp (1-31)"
              type="number"
              min="1"
              max="31"
              value={dueDay}
              onChange={(e) => setDueDay(Number(e.target.value))}
              required
            />
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={isPassThrough}
              onChange={(e) => setIsPassThrough(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Là khoản thu hộ / dịch vụ chuyển giao cho nhà cung cấp</span>
          </label>

          <Input
            label="Mô tả chi tiết khoản thu"
            placeholder="Căn cứ pháp lý, quy chế áp dụng..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddModalOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Xác nhận lưu
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal Edit Fee Type */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title={`Chỉnh sửa khoản thu: ${selectedFee?.code}`}
        description="Cập nhật tên, đơn vị tính, chu kỳ và hạn nộp của khoản thu."
      >
        <form onSubmit={handleUpdateFee} className="space-y-4">
          <Input
            label="Tên khoản thu"
            placeholder="Ví dụ: Phí quản lý vận hành tòa nhà..."
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Đơn vị tính"
              placeholder="m², hộ, xe, kWh..."
              value={editUnitLabel}
              onChange={(e) => setEditUnitLabel(e.target.value)}
              required
            />
            <Input
              label="Hạn nộp phí hàng tháng (1-31)"
              type="number"
              min="1"
              max="31"
              value={editDueDay}
              onChange={(e) => setEditDueDay(Number(e.target.value))}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Chu kỳ thu phí</label>
            <select
              value={editCycle}
              onChange={(e) => setEditCycle(e.target.value as any)}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="MONTHLY">Hàng tháng</option>
              <option value="QUARTERLY">Hàng quý</option>
              <option value="YEARLY">Hàng năm</option>
            </select>
          </div>

          <Input
            label="Mô tả chi tiết"
            placeholder="Căn cứ pháp lý, quy chế áp dụng..."
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setEditModalOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu thay đổi
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Lịch sử & Cập nhật đơn giá (US-14) */}
      <Modal
        isOpen={ratesModalOpen}
        onClose={() => setRatesModalOpen(false)}
        size="lg"
        title={`Lịch sử đơn giá — ${ratesTargetFee?.name || ''}`}
        description={`Mã phí: ${ratesTargetFee?.code || ''} • Đơn vị tính: ${ratesTargetFee?.unit_label || ''}`}
      >
        <div className="space-y-5 text-xs">
          {ratesTargetFee?.status === 'ACTIVE' && (
            <form
              onSubmit={handleCreateRate}
              className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3"
            >
              <p className="font-bold text-slate-800">Thiết lập đơn giá mới</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label={`Đơn giá mới (VNĐ / ${ratesTargetFee.unit_label})`}
                  type="number"
                  min="0"
                  step="1"
                  placeholder="Ví dụ: 8000"
                  value={newUnitPrice}
                  onChange={(e) => setNewUnitPrice(e.target.value)}
                  required
                />
                <Input
                  label="Ngày bắt đầu hiệu lực"
                  type="date"
                  value={newEffectiveFrom}
                  onChange={(e) => setNewEffectiveFrom(e.target.value)}
                  required
                />
              </div>
              <p className="text-[11px] text-slate-500">
                * Khi lưu đơn giá mới, đơn giá đang mở hiệu lực trước đó sẽ tự động kết thúc vào ngày liền trước ngày hiệu lực mới.
              </p>
              <div className="flex justify-end">
                <Button variant="primary" size="sm" type="submit" isLoading={submittingRate}>
                  Áp dụng đơn giá mới
                </Button>
              </div>
            </form>
          )}

          <div>
            <h4 className="font-bold text-slate-800 mb-2">Lịch sử thay đổi đơn giá</h4>
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Đơn giá</th>
                    <th className="py-2.5 px-3">Hiệu lực từ</th>
                    <th className="py-2.5 px-3">Hiệu lực đến</th>
                    <th className="py-2.5 px-3 text-center">Trạng thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loadingRates ? (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-slate-400">
                        Đang tải lịch sử đơn giá...
                      </td>
                    </tr>
                  ) : ratesList.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-slate-400">
                        Chưa có đơn giá nào được thiết lập cho khoản thu này.
                      </td>
                    </tr>
                  ) : (
                    ratesList.map((rate) => (
                      <tr key={rate.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                          {formatVND(rate.unit_price)}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">
                          {rate.effective_from}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-500">
                          {rate.effective_to || 'Chưa kết thúc'}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {!rate.effective_to ? (
                            <Badge variant="success" size="sm">
                              Đang mở hiệu lực
                            </Badge>
                          ) : (
                            <Badge variant="neutral" size="sm">
                              Đã khép kỳ
                            </Badge>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button variant="outline" size="sm" onClick={() => setRatesModalOpen(false)}>
              Đóng
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
