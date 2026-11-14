import React, { useEffect, useState } from 'react';
import {
  FileText,
  Plus,
  ShieldCheck,
  Ban,
  Clock,
  Sparkles,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { FeeType, FeeExemption } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';
import { INITIAL_FEE_EXEMPTIONS } from '../../api/mockData';

export const FeeCatalogPage: React.FC = () => {
  const { success, error } = useToast();
  const [feeTypes, setFeeTypes] = useState<FeeType[]>([]);
  const [exemptions, setExemptions] = useState<FeeExemption[]>(INITIAL_FEE_EXEMPTIONS);

  // Add Fee Modal
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [feeGroup, setFeeGroup] = useState<'MANAGEMENT' | 'PARKING' | 'UTILITY' | 'OTHER'>('MANAGEMENT');
  const [calcMethod, setCalcMethod] = useState<'PER_M2' | 'PER_HOUSEHOLD' | 'PER_PERSON' | 'PER_VEHICLE' | 'METERED'>('PER_M2');
  const [unitLabel, setUnitLabel] = useState('m²');
  const [unitPrice, setUnitPrice] = useState(7000);
  const [description, setDescription] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await ApiClient.getFeeTypes();
      setFeeTypes(data);
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleAddFee = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await ApiClient.addFeeType({
        code,
        name,
        fee_group: feeGroup,
        calc_method: calcMethod,
        unit_label: unitLabel,
        current_unit_price: unitPrice,
        description,
      });
      success(`Đã thêm khoản thu ${name} thành công!`);
      setAddModalOpen(false);
      setCode('');
      setName('');
      loadData();
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleDeactivate = async (id: number, feeName: string) => {
    if (!window.confirm(`Bạn có chắc muốn ngừng áp dụng khoản thu "${feeName}"? (Hệ thống không xóa vật lý dữ liệu cũ theo AC-13.1)`)) {
      return;
    }
    try {
      await ApiClient.deactivateFeeType(id);
      success(`Đã ngừng kích hoạt khoản thu "${feeName}".`);
      loadData();
    } catch (err: any) {
      error(err.message);
    }
  };

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-600" />
            <span>Danh mục Khoản thu & Biểu phí (US-12, US-13, US-14)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Cấu hình các khoản phí bắt buộc (theo diện tích, cố định theo hộ/xe), lưu vết lịch sử đơn giá và chính sách miễn giảm.
          </p>
        </div>

        <Button
          onClick={() => setAddModalOpen(true)}
          variant="primary"
          icon={<Plus className="w-4 h-4" />}
        >
          Tạo khoản thu mới
        </Button>
      </div>

      {/* Fee Types Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh mục khoản thu bắt buộc</h3>
          <span className="text-xs text-slate-500">Quy tắc AC-13.1: Không xóa vật lý dữ liệu đã phát sinh hóa đơn</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3.5 px-4">Mã Khoản Thu</th>
                <th className="py-3.5 px-4">Tên khoản thu</th>
                <th className="py-3.5 px-4">Nhóm phí</th>
                <th className="py-3.5 px-4">Cách tính</th>
                <th className="py-3.5 px-4">Đơn vị</th>
                <th className="py-3.5 px-4 text-right">Đơn giá hiện tại</th>
                <th className="py-3.5 px-4 text-center">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {feeTypes.map((fee) => (
                <tr key={fee.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-bold text-blue-700">{fee.code}</td>
                  <td className="py-3.5 px-4 font-semibold text-slate-900">{fee.name}</td>
                  <td className="py-3.5 px-4">
                    <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-medium">
                      {fee.fee_group}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-700 font-mono">
                    {fee.calc_method === 'PER_M2'
                      ? 'Theo m² diện tích'
                      : fee.calc_method === 'PER_VEHICLE'
                      ? 'Theo số lượng xe'
                      : fee.calc_method === 'METERED'
                      ? 'Theo công tơ (m³)'
                      : 'Cố định theo hộ'}
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">{fee.unit_label}</td>
                  <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900">
                    {formatVND(fee.current_unit_price || 0)}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <Badge variant={fee.status === 'ACTIVE' ? 'success' : 'neutral'} dot>
                      {fee.status === 'ACTIVE' ? 'Đang áp dụng' : 'Ngừng áp dụng'}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    {fee.status === 'ACTIVE' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-rose-600 hover:bg-rose-50"
                        onClick={() => handleDeactivate(fee.id, fee.name)}
                        icon={<Ban className="w-3.5 h-3.5" />}
                      >
                        Ngừng áp dụng
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fee Exemptions Table (US-15, US-16) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Chính sách miễn giảm theo hộ (US-15, US-16)</h3>
            <p className="text-xs text-slate-500 mt-0.5">Giảm trừ tự động khi động cơ tính phí chạy đầu tháng</p>
          </div>
          <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full font-semibold border border-emerald-200">
            {exemptions.length} hộ đang hưởng miễn giảm
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Mã Hộ</th>
                <th className="py-3 px-4">Khoản thu áp dụng</th>
                <th className="py-3 px-4">Mức miễn giảm</th>
                <th className="py-3 px-4">Lý do / Quyết định</th>
                <th className="py-3 px-4">Người phê duyệt</th>
                <th className="py-3 px-4">Thời hạn hiệu lực</th>
                <th className="py-3 px-4 text-center">Tình trạng</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {exemptions.map((ex) => (
                <tr key={ex.id} className="hover:bg-slate-50">
                  <td className="py-3 px-4 font-mono font-bold text-blue-700">{ex.household_code}</td>
                  <td className="py-3 px-4 font-medium text-slate-900">{ex.fee_name}</td>
                  <td className="py-3 px-4 font-bold text-emerald-600">
                    {ex.discount_type === 'PERCENT' ? `Giảm ${ex.discount_value}%` : `Giảm ${formatVND(ex.discount_value)}`}
                  </td>
                  <td className="py-3 px-4 text-slate-700">
                    <span>{ex.reason}</span>
                    {ex.decision_no && <span className="block text-[11px] text-slate-400 font-mono">({ex.decision_no})</span>}
                  </td>
                  <td className="py-3 px-4 text-slate-800">{ex.approved_by_name}</td>
                  <td className="py-3 px-4 text-slate-600">
                    {ex.valid_from} đến {ex.valid_to || 'Vô thời hạn'}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <Badge variant="success" dot size="sm">
                      Đang hiệu lực
                    </Badge>
                  </td>
                </tr>
              ))}
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
            placeholder="Ví dụ: PHI_VE_SINH, PHI_BE_BOI..."
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            required
          />
          <Input
            label="Tên khoản thu"
            placeholder="Ví dụ: Phí vệ sinh môi trường..."
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
                <option value="MANAGEMENT">Quản lý tòa nhà</option>
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
                <option value="PER_VEHICLE">Theo số lượng xe</option>
                <option value="METERED">Theo chỉ số công tơ</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Đơn vị tính"
              placeholder="m², hộ, xe, m³..."
              value={unitLabel}
              onChange={(e) => setUnitLabel(e.target.value)}
              required
            />
            <Input
              label="Đơn giá ban đầu (VNĐ)"
              type="number"
              min="0"
              step="500"
              value={unitPrice}
              onChange={(e) => setUnitPrice(Number(e.target.value))}
              required
            />
          </div>

          <Input
            label="Mô tả khoản thu"
            placeholder="Căn cứ pháp lý, chu kỳ áp dụng..."
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
