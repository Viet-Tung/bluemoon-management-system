import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  BadgePercent,
  Plus,
  RefreshCw,
  AlertCircle,
  Ban,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { DiscountType, FeeExemption, FeeType, Household } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 20;

export const FeeExemptionsPage: React.FC = () => {
  const { success, error: toastError } = useToast();

  const [exemptions, setExemptions] = useState<FeeExemption[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [feeTypes, setFeeTypes] = useState<FeeType[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [householdFilter, setHouseholdFilter] = useState('ALL');
  const [feeTypeFilter, setFeeTypeFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Create Modal
  const [addOpen, setAddOpen] = useState(false);
  const [householdId, setHouseholdId] = useState<number | ''>('');
  const [feeTypeId, setFeeTypeId] = useState<number | ''>('');
  const [discountType, setDiscountType] = useState<DiscountType>('PERCENT');
  const [discountValue, setDiscountValue] = useState('');
  const [validFrom, setValidFrom] = useState(() => new Date().toISOString().split('T')[0]);
  const [validTo, setValidTo] = useState('');
  const [decisionNo, setDecisionNo] = useState('');
  const [reason, setReason] = useState('');

  const loadRefs = useCallback(async () => {
    try {
      const [hhItems, feeItems] = await Promise.all([
        ApiClient.fetchAllPages((page, pageSize) =>
          ApiClient.getHouseholds({ page, page_size: pageSize })
        ),
        ApiClient.fetchAllPages((page, pageSize) =>
          ApiClient.getFeeTypes({ page, page_size: pageSize })
        ),
      ]);
      setHouseholds(hhItems);
      setFeeTypes(feeItems);
    } catch {
      // Main list error handler covers connectivity
    }
  }, []);

  const loadExemptions = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await ApiClient.getFeeExemptions({
        page,
        page_size: PAGE_SIZE,
        household_id: householdFilter !== 'ALL' ? Number(householdFilter) : undefined,
        fee_type_id: feeTypeFilter !== 'ALL' ? Number(feeTypeFilter) : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
      });
      setExemptions(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách chính sách miễn giảm.';
      setErrorMessage(msg);
      toastError(msg);
    } finally {
      setLoading(false);
    }
  }, [page, householdFilter, feeTypeFilter, statusFilter, toastError]);

  useEffect(() => {
    loadRefs();
  }, [loadRefs]);

  useEffect(() => {
    loadExemptions();
  }, [loadExemptions]);

  const householdMap = useMemo(() => {
    const map = new Map<number, Household>();
    households.forEach((h) => map.set(h.id, h));
    return map;
  }, [households]);

  const feeTypeMap = useMemo(() => {
    const map = new Map<number, FeeType>();
    feeTypes.forEach((f) => map.set(f.id, f));
    return map;
  }, [feeTypes]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!householdId || !feeTypeId) {
      toastError('Vui lòng chọn hộ gia đình và khoản thu.');
      return;
    }

    const val = Number(discountValue);
    if (isNaN(val) || val <= 0) {
      toastError('Giá trị miễn giảm phải lớn hơn 0.');
      return;
    }
    if (discountType === 'AMOUNT' && !Number.isInteger(val)) {
      toastError('Số tiền miễn giảm (VNĐ) phải là số nguyên, không được chứa phần thập phân.');
      return;
    }
    if (discountType === 'PERCENT' && val > 100) {
      toastError('Mức miễn giảm theo phần trăm không được vượt quá 100%.');
      return;
    }
    if (validTo && validTo < validFrom) {
      toastError('Ngày kết thúc hiệu lực không được nhỏ hơn ngày bắt đầu.');
      return;
    }

    try {
      await ApiClient.createFeeExemption({
        household_id: Number(householdId),
        fee_type_id: Number(feeTypeId),
        discount_type: discountType,
        discount_value: val,
        reason: reason.trim(),
        decision_no: decisionNo.trim() || undefined,
        valid_from: validFrom,
        valid_to: validTo || undefined,
      });
      success('Đã ban hành chính sách miễn giảm phí thành công!');
      setAddOpen(false);
      setDiscountValue('');
      setValidTo('');
      setDecisionNo('');
      setReason('');
      loadExemptions();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleRevoke = async (ex: FeeExemption) => {
    const hh = householdMap.get(ex.household_id);
    const fee = feeTypeMap.get(ex.fee_type_id);
    if (
      !window.confirm(
        `Bạn có chắc muốn thu hồi chính sách miễn giảm của hộ ${hh?.household_code || `#${ex.household_id}`} đối với khoản "${fee?.name || `#${ex.fee_type_id}`}"?`
      )
    ) {
      return;
    }
    try {
      await ApiClient.revokeFeeExemption(ex.id);
      success('Đã thu hồi chính sách miễn giảm.');
      loadExemptions();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const formatDiscount = (ex: FeeExemption) => {
    if (ex.discount_type === 'PERCENT') {
      return `${ex.discount_value}%`;
    }
    return new Intl.NumberFormat('vi-VN').format(ex.discount_value) + ' đ';
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <BadgePercent className="w-6 h-6 text-blue-600" />
            <span>Chính sách Miễn giảm phí</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Quản lý các quyết định miễn giảm theo phần trăm hoặc số tiền cố định cho từng hộ gia đình.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadExemptions}
            isLoading={loading}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setAddOpen(true)}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Tạo chính sách miễn giảm
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Không thể tải dữ liệu miễn giảm</p>
              <p className="text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={loadExemptions}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Hộ gia đình</label>
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
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Khoản thu áp dụng</label>
          <select
            value={feeTypeFilter}
            onChange={(e) => {
              setFeeTypeFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả khoản thu</option>
            {feeTypes.map((f) => (
              <option key={f.id} value={String(f.id)}>
                {f.code} - {f.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Trạng thái</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả trạng thái</option>
            <option value="ACTIVE">Đang hiệu lực</option>
            <option value="REVOKED">Đã thu hồi</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Danh sách miễn giảm phí</h3>
          <span className="text-xs text-slate-500 font-mono">Tổng số: {total} chính sách</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Hộ gia đình</th>
                <th className="py-3 px-4">Khoản thu</th>
                <th className="py-3 px-4">Mức giảm</th>
                <th className="py-3 px-4">Hiệu lực</th>
                <th className="py-3 px-4">Số QĐ & Lý do</th>
                <th className="py-3 px-4 text-center">Trạng thái</th>
                <th className="py-3 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {exemptions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    {loading ? 'Đang tải danh sách miễn giảm...' : 'Chưa có chính sách miễn giảm nào.'}
                  </td>
                </tr>
              ) : (
                exemptions.map((ex) => {
                  const hh = householdMap.get(ex.household_id);
                  const fee = feeTypeMap.get(ex.fee_type_id);
                  return (
                    <tr key={ex.id} className="hover:bg-slate-50">
                      <td className="py-3.5 px-4">
                        {hh ? (
                          <div>
                            <span className="font-mono font-bold text-blue-700">
                              {hh.household_code}
                            </span>
                            {hh.apartment_code && (
                              <span className="ml-1.5 text-[11px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono">
                                {hh.apartment_code}
                              </span>
                            )}
                            {hh.head_name && (
                              <p className="text-[11px] text-slate-500">{hh.head_name}</p>
                            )}
                          </div>
                        ) : (
                          <span className="font-mono">Hộ #{ex.household_id}</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {fee ? (
                          <div>
                            <span className="font-semibold text-slate-900">{fee.name}</span>
                            <p className="font-mono text-[11px] text-slate-400">{fee.code}</p>
                          </div>
                        ) : (
                          <span className="font-mono">Phí #{ex.fee_type_id}</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-emerald-700">
                        {formatDiscount(ex)}
                        <p className="text-[10px] font-sans font-normal text-slate-400">
                          {ex.discount_type === 'PERCENT' ? 'Theo tỷ lệ %' : 'Số tiền cố định'}
                        </p>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">
                        <p>Từ: {ex.valid_from}</p>
                        <p className="text-[11px] text-slate-400">
                          Đến: {ex.valid_to || 'Không thời hạn'}
                        </p>
                      </td>
                      <td className="py-3.5 px-4 text-slate-700 max-w-xs">
                        {ex.decision_no && (
                          <span className="inline-block font-mono text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded mb-0.5">
                            QĐ: {ex.decision_no}
                          </span>
                        )}
                        <p className="truncate" title={ex.reason}>
                          {ex.reason}
                        </p>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <Badge
                          variant={ex.status === 'ACTIVE' ? 'success' : 'danger'}
                          dot
                          size="sm"
                        >
                          {ex.status === 'ACTIVE' ? 'Đang hiệu lực' : 'Đã thu hồi'}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {ex.status === 'ACTIVE' && (
                          <button
                            onClick={() => handleRevoke(ex)}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600 hover:text-rose-800 px-2 py-1 rounded hover:bg-rose-50 transition"
                            title="Thu hồi chính sách miễn giảm"
                          >
                            <Ban className="w-3.5 h-3.5" />
                            <span>Thu hồi</span>
                          </button>
                        )}
                      </td>
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

      {/* Modal: Tạo chính sách miễn giảm */}
      <Modal
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        title="Tạo chính sách miễn giảm phí"
        description="Áp dụng miễn hoặc giảm một khoản phí cho hộ gia đình trong khoảng thời gian xác định."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Hộ gia đình <span className="text-rose-500">*</span>
            </label>
            <select
              value={householdId}
              onChange={(e) => setHouseholdId(e.target.value ? Number(e.target.value) : '')}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              <option value="">-- Chọn hộ gia đình --</option>
              {households
                .filter((h) => h.status === 'ACTIVE')
                .map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.household_code} {h.apartment_code ? `(${h.apartment_code})` : ''} -{' '}
                    {h.head_name || 'Chưa rõ chủ hộ'}
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Khoản thu áp dụng <span className="text-rose-500">*</span>
            </label>
            <select
              value={feeTypeId}
              onChange={(e) => setFeeTypeId(e.target.value ? Number(e.target.value) : '')}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              <option value="">-- Chọn khoản thu --</option>
              {feeTypes
                .filter((f) => f.status === 'ACTIVE')
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.code} - {f.name}
                  </option>
                ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Hình thức giảm <span className="text-rose-500">*</span>
              </label>
              <select
                value={discountType}
                onChange={(e) => {
                  const nextType = e.target.value as DiscountType;
                  setDiscountType(nextType);
                  if (nextType === 'AMOUNT' && /[.,]/.test(discountValue)) {
                    setDiscountValue('');
                  }
                }}
                className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="PERCENT">Theo phần trăm (%)</option>
                <option value="AMOUNT">Số tiền cố định (VNĐ)</option>
              </select>
            </div>

            <Input
              label={discountType === 'PERCENT' ? 'Mức giảm (%)' : 'Số tiền giảm (VNĐ)'}
              type="number"
              step={discountType === 'AMOUNT' ? '1' : 'any'}
              min={discountType === 'AMOUNT' ? '1' : '0.01'}
              max={discountType === 'PERCENT' ? '100' : undefined}
              placeholder={discountType === 'PERCENT' ? 'Ví dụ: 50' : 'Ví dụ: 100000'}
              value={discountValue}
              onChange={(e) => setDiscountValue(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Hiệu lực từ ngày"
              type="date"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
              required
            />
            <Input
              label="Hiệu lực đến ngày (Tùy chọn)"
              type="date"
              min={validFrom}
              value={validTo}
              onChange={(e) => setValidTo(e.target.value)}
            />
          </div>

          <Input
            label="Số quyết định / Văn bản (Tùy chọn)"
            placeholder="Ví dụ: QĐ-01/2026-BQL"
            value={decisionNo}
            onChange={(e) => setDecisionNo(e.target.value)}
          />

          <Input
            label="Lý do miễn giảm"
            placeholder="Ví dụ: Gia đình chính sách, hộ có công..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Ban hành miễn giảm
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
