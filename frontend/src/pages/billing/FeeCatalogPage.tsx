import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  Plus,
  RefreshCw,
  AlertCircle,
  Ban,
  CheckCircle,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { FeeType, FeeGroup, CalcMethod, FeeCycle } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

export const FeeCatalogPage: React.FC = () => {
  const { success, error: toastError } = useToast();
  const [feeTypes, setFeeTypes] = useState<FeeType[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
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
  const [cycle, setCycle] = useState<FeeCycle>('MONTHLY');
  const [dueDay, setDueDay] = useState<number>(15);
  const [description, setDescription] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const params: any = { page: 1, page_size: 100 };
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (groupFilter !== 'ALL') params.fee_group = groupFilter;

      const data = await ApiClient.getFeeTypes(params);
      setFeeTypes(data.items || []);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh mục khoản thu từ máy chủ Backend.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, groupFilter, toastError]);

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
      loadData();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleDeactivate = async (id: number, feeName: string) => {
    if (
      !window.confirm(
        `Bạn có chắc muốn ngừng áp dụng khoản thu "${feeName}"? (Hệ thống không xóa vật lý dữ liệu cũ theo AC-13.1)`
      )
    ) {
      return;
    }
    try {
      await ApiClient.deactivateFeeType(id);
      success(`Đã ngừng kích hoạt khoản thu "${feeName}".`);
      loadData();
    } catch (err: any) {
      toastError(err.message);
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-600" />
            <span>Danh mục Khoản thu & Biểu phí (Sprint 1: US-12, US-13)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Cấu hình các danh mục phí bắt buộc: phí quản lý theo diện tích sàn, phí giữ xe, phí dịch vụ tòa nhà.
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

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Nhóm khoản thu</label>
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
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
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả trạng thái</option>
            <option value="ACTIVE">Đang áp dụng (ACTIVE)</option>
            <option value="INACTIVE">Đã ngừng áp dụng (INACTIVE)</option>
          </select>
        </div>
      </div>

      {/* Fee Catalog Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh mục khoản thu trong hệ thống</h3>
          <span className="text-xs text-slate-500 font-mono">Tổng số: {feeTypes.length} loại phí</span>
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
              {feeTypes.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải danh mục khoản thu...' : 'Không có khoản thu nào.'}
                  </td>
                </tr>
              ) : (
                feeTypes.map((fee) => (
                  <tr key={fee.id} className="hover:bg-slate-50">
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-700">{fee.code}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      <div>{fee.name}</div>
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
                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">{fee.unit_label}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900 font-mono">
                      {formatVND(fee.current_unit_price)}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <span>{fee.cycle === 'MONTHLY' ? 'Hàng tháng' : fee.cycle}</span>
                      {fee.due_day && <span className="text-slate-400"> (Ngày {fee.due_day})</span>}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge variant={fee.status === 'ACTIVE' ? 'success' : 'danger'} dot size="sm">
                        {fee.status === 'ACTIVE' ? 'Đang dùng' : 'Đã ngừng'}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {fee.status === 'ACTIVE' && (
                        <button
                          onClick={() => handleDeactivate(fee.id, fee.name)}
                          className="text-[11px] font-semibold text-rose-600 hover:text-rose-800 px-2 py-1 rounded hover:bg-rose-50 transition"
                          title="Ngừng áp dụng khoản thu (US-13, AC-13.1)"
                        >
                          Ngừng áp dụng
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Add Fee Type */}
      <Modal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title="Tạo khoản thu bắt buộc mới (US-12)"
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
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Cách tính toán</label>
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

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Đơn vị tính"
              placeholder="m², hộ, xe, kWh..."
              value={unitLabel}
              onChange={(e) => setUnitLabel(e.target.value)}
              required
            />
            <Input
              label="Hạn nộp phí hàng tháng (1-31)"
              type="number"
              min="1"
              max="31"
              value={dueDay}
              onChange={(e) => setDueDay(Number(e.target.value))}
              required
            />
          </div>

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
    </div>
  );
};
