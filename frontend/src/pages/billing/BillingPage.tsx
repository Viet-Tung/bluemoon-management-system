import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
  Receipt,
  CalendarRange,
  Gauge,
  Plus,
  RefreshCw,
  AlertCircle,
  Play,
  Lock,
  Eye,
  Printer,
  Pencil,
  CheckCircle2,
} from 'lucide-react';
import { ApiClient } from '../../api';
import {
  BillingPeriod,
  FeeType,
  GenerateResult,
  Household,
  Invoice,
  InvoiceDetail,
  UtilityReading,
} from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';

const PAGE_SIZE = 20;

const formatVND = (num?: number | null) => {
  if (num === null || num === undefined) return '0 đ';
  return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
};

export const BillingPage: React.FC = () => {
  const { success, error: toastError } = useToast();

  const [activeTab, setActiveTab] = useState<'periods' | 'utilities' | 'invoices'>('periods');

  // Shared Reference Lists
  const [allPeriods, setAllPeriods] = useState<BillingPeriod[]>([]);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [feeTypes, setFeeTypes] = useState<FeeType[]>([]);

  // TAB 1: Billing Periods State
  const [periods, setPeriods] = useState<BillingPeriod[]>([]);
  const [periodsTotal, setPeriodsTotal] = useState(0);
  const [periodsPage, setPeriodsPage] = useState(1);
  const [periodStatusFilter, setPeriodStatusFilter] = useState('ALL');
  const [periodYearFilter, setPeriodYearFilter] = useState('');
  const [debouncedPeriodYear, setDebouncedPeriodYear] = useState<number | undefined>(undefined);
  const [periodYearError, setPeriodYearError] = useState<string | null>(null);
  const [loadingPeriods, setLoadingPeriods] = useState(false);

  useEffect(() => {
    const trimmed = periodYearFilter.trim();
    if (!trimmed) {
      setPeriodYearError(null);
      setPeriodsPage(1);
      setDebouncedPeriodYear(undefined);
      return;
    }

    if (!/^\d+$/.test(trimmed)) {
      setPeriodYearError('Năm lọc chỉ được chứa chữ số (2000–2100).');
      return;
    }

    if (trimmed.length < 4) {
      setPeriodYearError(null);
      return;
    }

    const parsed = Number(trimmed);
    if (!/^\d{4}$/.test(trimmed) || parsed < 2000 || parsed > 2100) {
      setPeriodYearError('Năm hợp lệ phải từ 2000 đến 2100.');
      return;
    }

    setPeriodYearError(null);
    const timer = setTimeout(() => {
      setPeriodsPage(1);
      setDebouncedPeriodYear(parsed);
    }, 300);
    return () => clearTimeout(timer);
  }, [periodYearFilter]);
  const [periodsError, setPeriodsError] = useState<string | null>(null);

  // Create Period Modal
  const [createPeriodOpen, setCreatePeriodOpen] = useState(false);
  const [newMonth, setNewMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
  const [newPeriodName, setNewPeriodName] = useState(() => {
    const d = new Date();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `Kỳ thu tháng ${m}/${d.getFullYear()}`;
  });
  const [newDueDate, setNewDueDate] = useState('');
  const [creatingPeriod, setCreatingPeriod] = useState(false);

  // Period Detail / Generate / Close
  const [periodDetail, setPeriodDetail] = useState<BillingPeriod | null>(null);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [generateResult, setGenerateResult] = useState<{
    period: BillingPeriod;
    result: GenerateResult;
  } | null>(null);
  const [closingId, setClosingId] = useState<number | null>(null);

  // TAB 2: Utility Readings State
  const [readings, setReadings] = useState<UtilityReading[]>([]);
  const [readingsTotal, setReadingsTotal] = useState(0);
  const [readingsPage, setReadingsPage] = useState(1);
  const [utilPeriodFilter, setUtilPeriodFilter] = useState('ALL');
  const [utilFeeFilter, setUtilFeeFilter] = useState('ALL');
  const [utilHouseholdFilter, setUtilHouseholdFilter] = useState('ALL');
  const [loadingReadings, setLoadingReadings] = useState(false);
  const [readingsError, setReadingsError] = useState<string | null>(null);

  // Create Utility Reading Modal
  const [addReadingOpen, setAddReadingOpen] = useState(false);
  const [readPeriodId, setReadPeriodId] = useState<number | ''>('');
  const [readHouseholdId, setReadHouseholdId] = useState<number | ''>('');
  const [readFeeTypeId, setReadFeeTypeId] = useState<number | ''>('');
  const [prevIndex, setPrevIndex] = useState('0');
  const [currIndex, setCurrIndex] = useState('');
  const [readUnitPrice, setReadUnitPrice] = useState('');

  // Edit Utility Reading Modal
  const [editReadingOpen, setEditReadingOpen] = useState(false);
  const [editReadingTarget, setEditReadingTarget] = useState<UtilityReading | null>(null);
  const [editPrevIndex, setEditPrevIndex] = useState('');
  const [editCurrIndex, setEditCurrIndex] = useState('');
  const [editReadUnitPrice, setEditReadUnitPrice] = useState('');

  // TAB 3: Invoices State
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoicesTotal, setInvoicesTotal] = useState(0);
  const [invoicesPage, setInvoicesPage] = useState(1);
  const [invPeriodFilter, setInvPeriodFilter] = useState('ALL');
  const [invHouseholdFilter, setInvHouseholdFilter] = useState('ALL');
  const [invStatusFilter, setInvStatusFilter] = useState('ALL');
  const [loadingInvoices, setLoadingInvoices] = useState(false);
  const [invoicesError, setInvoicesError] = useState<string | null>(null);

  // Invoice Detail / Print Modal
  const [invoiceDetail, setInvoiceDetail] = useState<InvoiceDetail | null>(null);
  const [loadingInvoiceDetail, setLoadingInvoiceDetail] = useState(false);

  const loadRefs = useCallback(async () => {
    try {
      const [allP, hhItems, feeItems] = await Promise.all([
        ApiClient.fetchAllPages((page, pageSize) =>
          ApiClient.getBillingPeriods({ page, page_size: pageSize })
        ),
        ApiClient.fetchAllPages((page, pageSize) =>
          ApiClient.getHouseholds({ page, page_size: pageSize })
        ),
        ApiClient.fetchAllPages((page, pageSize) =>
          ApiClient.getFeeTypes({ page, page_size: pageSize })
        ),
      ]);
      setAllPeriods(allP);
      setHouseholds(hhItems);
      setFeeTypes(feeItems);
    } catch {
      // Tab loaders handle connectivity errors visibly
    }
  }, []);

  const loadPeriods = useCallback(async () => {
    setLoadingPeriods(true);
    setPeriodsError(null);
    try {
      const res = await ApiClient.getBillingPeriods({
        page: periodsPage,
        page_size: PAGE_SIZE,
        status: periodStatusFilter !== 'ALL' ? periodStatusFilter : undefined,
        year: debouncedPeriodYear,
      });
      setPeriods(res.items || []);
      setPeriodsTotal(res.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách kỳ thu phí.';
      setPeriodsError(msg);
      toastError(msg);
    } finally {
      setLoadingPeriods(false);
    }
  }, [periodsPage, periodStatusFilter, debouncedPeriodYear, toastError]);

  const loadReadings = useCallback(async () => {
    setLoadingReadings(true);
    setReadingsError(null);
    try {
      const res = await ApiClient.getUtilityReadings({
        page: readingsPage,
        page_size: PAGE_SIZE,
        billing_period_id:
          utilPeriodFilter !== 'ALL' ? Number(utilPeriodFilter) : undefined,
        fee_type_id: utilFeeFilter !== 'ALL' ? Number(utilFeeFilter) : undefined,
        household_id:
          utilHouseholdFilter !== 'ALL' ? Number(utilHouseholdFilter) : undefined,
      });
      setReadings(res.items || []);
      setReadingsTotal(res.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách chỉ số điện/nước.';
      setReadingsError(msg);
      toastError(msg);
    } finally {
      setLoadingReadings(false);
    }
  }, [readingsPage, utilPeriodFilter, utilFeeFilter, utilHouseholdFilter, toastError]);

  const loadInvoices = useCallback(async () => {
    setLoadingInvoices(true);
    setInvoicesError(null);
    try {
      const res = await ApiClient.getInvoices({
        page: invoicesPage,
        page_size: PAGE_SIZE,
        billing_period_id:
          invPeriodFilter !== 'ALL' ? Number(invPeriodFilter) : undefined,
        household_id:
          invHouseholdFilter !== 'ALL' ? Number(invHouseholdFilter) : undefined,
        status: invStatusFilter !== 'ALL' ? invStatusFilter : undefined,
      });
      setInvoices(res.items || []);
      setInvoicesTotal(res.total || 0);
    } catch (err: any) {
      const msg = err.message || 'Không thể tải danh sách giấy báo nộp phí.';
      setInvoicesError(msg);
      toastError(msg);
    } finally {
      setLoadingInvoices(false);
    }
  }, [invoicesPage, invPeriodFilter, invHouseholdFilter, invStatusFilter, toastError]);

  useEffect(() => {
    loadRefs();
  }, [loadRefs]);

  useEffect(() => {
    if (activeTab === 'periods') loadPeriods();
  }, [activeTab, loadPeriods]);

  useEffect(() => {
    if (activeTab === 'utilities') loadReadings();
  }, [activeTab, loadReadings]);

  useEffect(() => {
    if (activeTab === 'invoices') loadInvoices();
  }, [activeTab, loadInvoices]);

  const periodMap = useMemo(() => {
    const m = new Map<number, BillingPeriod>();
    allPeriods.forEach((p) => m.set(p.id, p));
    return m;
  }, [allPeriods]);

  const meteredFees = useMemo(
    () =>
      feeTypes.filter(
        (f) =>
          f.status === 'ACTIVE' &&
          (f.calc_method === 'METERED' || (f.calc_method as string) === 'PER_INDEX')
      ),
    [feeTypes]
  );

  // Handlers: Billing Periods
  const handleMonthChange = (val: string) => {
    setNewMonth(val);
    if (val && /^\d{4}-\d{2}$/.test(val)) {
      const [y, m] = val.split('-');
      setNewPeriodName(`Kỳ thu tháng ${m}/${y}`);
    }
  };

  const handleCreatePeriod = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{4}-\d{2}$/.test(newMonth)) {
      toastError('Vui lòng chọn tháng hợp lệ.');
      return;
    }
    const periodMonth = `${newMonth}-01`;
    if (newDueDate && newDueDate < periodMonth) {
      toastError('Hạn nộp phí phải từ ngày đầu kỳ thu trở đi.');
      return;
    }

    setCreatingPeriod(true);
    try {
      await ApiClient.createBillingPeriod({
        period_month: periodMonth,
        name: newPeriodName.trim(),
        due_date: newDueDate || undefined,
      });
      success(`Đã tạo ${newPeriodName.trim()} thành công!`);
      setCreatePeriodOpen(false);
      setNewDueDate('');
      loadPeriods();
      loadRefs();
    } catch (err: any) {
      toastError(err.message);
    } finally {
      setCreatingPeriod(false);
    }
  };

  const handleViewPeriod = async (id: number) => {
    try {
      const p = await ApiClient.getBillingPeriod(id);
      setPeriodDetail(p);
    } catch (err: any) {
      toastError(err.message || 'Không thể tải chi tiết kỳ thu.');
    }
  };

  const handleGenerate = async (p: BillingPeriod) => {
    if (
      !window.confirm(
        `Chạy tính phí tự động cho "${p.name}"? Hệ thống sẽ tính phí quản lý, phí gửi xe, chỉ số điện/nước đã nhập và áp dụng miễn giảm cho các hộ đang cư trú.`
      )
    ) {
      return;
    }
    setGeneratingId(p.id);
    try {
      const res = await ApiClient.generateBillingInvoices(p.id);
      setGenerateResult({ period: p, result: res });
      success(
        `Đã tính phí xong: ${res.invoices_created} giấy báo phí (${formatVND(res.total_fee_amount)}).`
      );
      loadPeriods();
      loadRefs();
    } catch (err: any) {
      toastError(err.message);
    } finally {
      setGeneratingId(null);
    }
  };

  const handleClosePeriod = async (p: BillingPeriod) => {
    if (
      !window.confirm(
        `Bạn có chắc muốn CHỐT "${p.name}"? Sau khi chốt kỳ thu, không thể chạy lại tính phí hoặc chỉnh sửa chỉ số điện/nước của kỳ này.`
      )
    ) {
      return;
    }
    setClosingId(p.id);
    try {
      await ApiClient.closeBillingPeriod(p.id);
      success(`Đã chốt kỳ thu "${p.name}" thành công!`);
      loadPeriods();
      loadRefs();
    } catch (err: any) {
      toastError(err.message);
    } finally {
      setClosingId(null);
    }
  };

  // Handlers: Utility Readings
  const handleAddReading = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!readPeriodId || !readHouseholdId || !readFeeTypeId) {
      toastError('Vui lòng chọn đầy đủ kỳ thu, hộ gia đình và khoản thu.');
      return;
    }
    const prevVal = Number(prevIndex);
    const currVal = Number(currIndex);
    if (isNaN(prevVal) || prevVal < 0 || isNaN(currVal) || currVal < prevVal) {
      toastError('Chỉ số mới phải lớn hơn hoặc bằng chỉ số cũ (>= 0).');
      return;
    }

    let priceVal: number | undefined = undefined;
    if (readUnitPrice.trim() !== '') {
      priceVal = Number(readUnitPrice);
      if (isNaN(priceVal) || !Number.isInteger(priceVal) || priceVal < 0) {
        toastError('Đơn giá phải là số nguyên không âm.');
        return;
      }
    }

    try {
      await ApiClient.createUtilityReading({
        billing_period_id: Number(readPeriodId),
        household_id: Number(readHouseholdId),
        fee_type_id: Number(readFeeTypeId),
        previous_index: prevVal,
        current_index: currVal,
        unit_price: priceVal,
      });
      success('Đã lưu chỉ số điện/nước thành công!');
      setAddReadingOpen(false);
      setPrevIndex('0');
      setCurrIndex('');
      setReadUnitPrice('');
      loadReadings();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  const handleEditReading = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editReadingTarget) return;
    const prevVal = Number(editPrevIndex);
    const currVal = Number(editCurrIndex);
    if (isNaN(prevVal) || prevVal < 0 || isNaN(currVal) || currVal < prevVal) {
      toastError('Chỉ số mới phải lớn hơn hoặc bằng chỉ số cũ (>= 0).');
      return;
    }

    let priceVal: number | undefined = undefined;
    if (editReadUnitPrice.trim() !== '') {
      priceVal = Number(editReadUnitPrice);
      if (isNaN(priceVal) || !Number.isInteger(priceVal) || priceVal < 0) {
        toastError('Đơn giá phải là số nguyên không âm.');
        return;
      }
    }

    try {
      await ApiClient.updateUtilityReading(editReadingTarget.id, {
        previous_index: prevVal,
        current_index: currVal,
        unit_price: priceVal,
      });
      success('Đã cập nhật chỉ số công tơ thành công!');
      setEditReadingOpen(false);
      setEditReadingTarget(null);
      loadReadings();
    } catch (err: any) {
      toastError(err.message);
    }
  };

  // Handlers: Invoices
  const handleOpenInvoice = async (invId: number) => {
    setLoadingInvoiceDetail(true);
    try {
      const detail = await ApiClient.getInvoice(invId);
      setInvoiceDetail(detail);
    } catch (err: any) {
      toastError(err.message || 'Không thể tải chi tiết giấy báo nộp phí.');
    } finally {
      setLoadingInvoiceDetail(false);
    }
  };

  const getPeriodStatusBadge = (status: string) => {
    switch (status) {
      case 'DRAFT':
        return <Badge variant="neutral" dot size="sm">Nháp (Chưa tính phí)</Badge>;
      case 'OPEN':
        return <Badge variant="info" dot size="sm">Đang thu phí</Badge>;
      case 'CLOSED':
        return <Badge variant="success" dot size="sm">Đã chốt kỳ</Badge>;
      default:
        return <Badge size="sm">{status}</Badge>;
    }
  };

  const getInvoiceStatusBadge = (status: string) => {
    switch (status) {
      case 'PAID':
        return <Badge variant="paid" dot size="sm">Đã nộp đủ</Badge>;
      case 'PARTIAL':
        return <Badge variant="partial" dot size="sm">Nộp một phần</Badge>;
      case 'UNPAID':
        return <Badge variant="unpaid" dot size="sm">Chưa nộp</Badge>;
      default:
        return <Badge size="sm">{status}</Badge>;
    }
  };

  const periodsTotalPages = Math.max(1, Math.ceil(periodsTotal / PAGE_SIZE));
  const readingsTotalPages = Math.max(1, Math.ceil(readingsTotal / PAGE_SIZE));
  const invoicesTotalPages = Math.max(1, Math.ceil(invoicesTotal / PAGE_SIZE));

  const previewConsumption = useMemo(() => {
    const p = Number(prevIndex);
    const c = Number(currIndex);
    if (currIndex === '' || isNaN(p) || isNaN(c)) return null;
    return c - p;
  }, [prevIndex, currIndex]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 no-print">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Receipt className="w-6 h-6 text-blue-600" />
            <span>Kỳ thu, Chỉ số Điện/Nước & Giấy báo phí</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Quản lý kỳ tính phí hàng tháng, ghi nhận chỉ số công tơ, tính phí tự động và phát hành giấy báo nộp phí.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              loadRefs();
              if (activeTab === 'periods') loadPeriods();
              if (activeTab === 'utilities') loadReadings();
              if (activeTab === 'invoices') loadInvoices();
            }}
            isLoading={loadingPeriods || loadingReadings || loadingInvoices}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
          {activeTab === 'periods' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setCreatePeriodOpen(true)}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              Tạo kỳ thu mới
            </Button>
          )}
          {activeTab === 'utilities' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setAddReadingOpen(true)}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              Nhập chỉ số mới
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto no-print">
        <button
          onClick={() => setActiveTab('periods')}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition whitespace-nowrap ${
            activeTab === 'periods'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <CalendarRange className="w-4 h-4" />
          <span>Kỳ thu & Tính phí ({allPeriods.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('utilities')}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition whitespace-nowrap ${
            activeTab === 'utilities'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Gauge className="w-4 h-4" />
          <span>Chỉ số Điện / Nước</span>
        </button>

        <button
          onClick={() => setActiveTab('invoices')}
          className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition whitespace-nowrap ${
            activeTab === 'invoices'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Receipt className="w-4 h-4" />
          <span>Giấy báo nộp phí</span>
        </button>
      </div>

      {/* TAB 1: BILLING PERIODS */}
      {activeTab === 'periods' && (
        <div className="space-y-4 no-print">
          {periodsError && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
                <span>{periodsError}</span>
              </div>
              <Button size="sm" variant="outline" onClick={loadPeriods}>
                Thử lại
              </Button>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Trạng thái kỳ thu</label>
              <select
                value={periodStatusFilter}
                onChange={(e) => {
                  setPeriodStatusFilter(e.target.value);
                  setPeriodsPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả trạng thái</option>
                <option value="DRAFT">Nháp (Chưa tính phí)</option>
                <option value="OPEN">Đang thu phí</option>
                <option value="CLOSED">Đã chốt kỳ</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Lọc theo năm</label>
              <input
                type="number"
                min="2000"
                max="2100"
                placeholder="Ví dụ: 2026 (Để trống = tất cả)"
                value={periodYearFilter}
                onChange={(e) => setPeriodYearFilter(e.target.value)}
                className={`w-full bg-slate-50 border rounded-xl px-3 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2 ${
                  periodYearError
                    ? 'border-rose-400 focus:ring-rose-100'
                    : 'border-slate-300 focus:ring-blue-100'
                }`}
              />
              {periodYearError && (
                <p className="text-[11px] text-rose-600 mt-1">{periodYearError}</p>
              )}
              {!periodYearError &&
                periodYearFilter.trim().length > 0 &&
                periodYearFilter.trim().length < 4 && (
                  <p className="text-[11px] text-slate-400 mt-1">
                    Nhập đủ 4 chữ số năm (2000–2100)
                  </p>
                )}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Kỳ thu</th>
                    <th className="py-3 px-4">Tháng tính phí</th>
                    <th className="py-3 px-4">Hạn thanh toán</th>
                    <th className="py-3 px-4">Tính phí gần nhất</th>
                    <th className="py-3 px-4 text-center">Trạng thái</th>
                    <th className="py-3 px-4 text-right">Thao tác nghiệp vụ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {periods.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        {loadingPeriods ? 'Đang tải danh sách kỳ thu...' : 'Chưa có kỳ thu nào.'}
                      </td>
                    </tr>
                  ) : (
                    periods.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-50">
                        <td className="py-3.5 px-4 font-bold text-slate-900">{p.name}</td>
                        <td className="py-3.5 px-4 font-mono text-blue-700 font-semibold">
                          {p.period_month}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-600">
                          {p.due_date || '---'}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-500">
                          {p.generated_at
                            ? new Date(p.generated_at).toLocaleString('vi-VN')
                            : 'Chưa chạy'}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {getPeriodStatusBadge(p.status)}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5 flex-wrap">
                            <button
                              onClick={() => handleViewPeriod(p.id)}
                              className="text-[11px] font-semibold text-slate-600 hover:text-blue-600 px-2 py-1 rounded hover:bg-slate-100 transition inline-flex items-center gap-1"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>Chi tiết</span>
                            </button>
                            <button
                              onClick={() => {
                                setInvPeriodFilter(String(p.id));
                                setInvoicesPage(1);
                                setActiveTab('invoices');
                              }}
                              className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded hover:bg-indigo-50 transition"
                            >
                              Giấy báo phí
                            </button>
                            {p.status !== 'CLOSED' && (
                              <Button
                                variant="primary"
                                size="sm"
                                isLoading={generatingId === p.id}
                                onClick={() => handleGenerate(p)}
                                icon={<Play className="w-3 h-3" />}
                              >
                                {p.status === 'OPEN' ? 'Tính lại phí' : 'Tính phí tự động'}
                              </Button>
                            )}
                            {p.status === 'OPEN' && (
                              <Button
                                variant="outline"
                                size="sm"
                                isLoading={closingId === p.id}
                                onClick={() => handleClosePeriod(p)}
                                icon={<Lock className="w-3 h-3" />}
                              >
                                Chốt kỳ thu
                              </Button>
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
                Trang {periodsPage} / {periodsTotalPages} (Tổng {periodsTotal} kỳ thu)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={periodsPage <= 1 || loadingPeriods}
                  onClick={() => setPeriodsPage((p) => Math.max(1, p - 1))}
                >
                  Trang trước
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={periodsPage >= periodsTotalPages || loadingPeriods}
                  onClick={() => setPeriodsPage((p) => Math.min(periodsTotalPages, p + 1))}
                >
                  Trang sau
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: UTILITY READINGS */}
      {activeTab === 'utilities' && (
        <div className="space-y-4 no-print">
          {meteredFees.length === 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-900">
              Chưa có khoản thu nào có phương pháp tính <strong>Theo chỉ số công tơ</strong> đang hoạt động. Vui lòng tạo khoản thu Điện/Nước tại Danh mục Khoản thu trước khi nhập chỉ số.
            </div>
          )}

          {readingsError && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
                <span>{readingsError}</span>
              </div>
              <Button size="sm" variant="outline" onClick={loadReadings}>
                Thử lại
              </Button>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Kỳ thu</label>
              <select
                value={utilPeriodFilter}
                onChange={(e) => {
                  setUtilPeriodFilter(e.target.value);
                  setReadingsPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả kỳ thu</option>
                {allPeriods.map((p) => (
                  <option key={p.id} value={String(p.id)}>
                    {p.name} ({p.period_month})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Loại dịch vụ (Công tơ)</label>
              <select
                value={utilFeeFilter}
                onChange={(e) => {
                  setUtilFeeFilter(e.target.value);
                  setReadingsPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả khoản thu chỉ số</option>
                {meteredFees.map((f) => (
                  <option key={f.id} value={String(f.id)}>
                    {f.code} - {f.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Hộ gia đình</label>
              <select
                value={utilHouseholdFilter}
                onChange={(e) => {
                  setUtilHouseholdFilter(e.target.value);
                  setReadingsPage(1);
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
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Kỳ thu</th>
                    <th className="py-3 px-4">Hộ gia đình</th>
                    <th className="py-3 px-4">Dịch vụ</th>
                    <th className="py-3 px-4 text-right">Chỉ số cũ</th>
                    <th className="py-3 px-4 text-right">Chỉ số mới</th>
                    <th className="py-3 px-4 text-right">Tiêu thụ</th>
                    <th className="py-3 px-4 text-right">Đơn giá</th>
                    <th className="py-3 px-4 text-right">Thành tiền</th>
                    <th className="py-3 px-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {readings.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-slate-400">
                        {loadingReadings ? 'Đang tải danh sách chỉ số...' : 'Chưa có dữ liệu chỉ số nào.'}
                      </td>
                    </tr>
                  ) : (
                    readings.map((r) => {
                      const period = periodMap.get(r.billing_period_id);
                      const isClosed = period?.status === 'CLOSED';
                      return (
                        <tr key={r.id} className="hover:bg-slate-50">
                          <td className="py-3.5 px-4 text-slate-700 font-medium">
                            {period ? period.name : `Kỳ #${r.billing_period_id}`}
                          </td>
                          <td className="py-3.5 px-4 font-mono font-bold text-blue-700">
                            {r.household_code}
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-slate-800">{r.fee_name}</td>
                          <td className="py-3.5 px-4 text-right font-mono text-slate-600">
                            {r.previous_index}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-slate-900 font-semibold">
                            {r.current_index}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono font-bold text-indigo-700">
                            {r.consumption}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-slate-600">
                            {formatVND(r.unit_price)}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900">
                            {formatVND(r.amount)}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            {!isClosed ? (
                              <button
                                onClick={() => {
                                  setEditReadingTarget(r);
                                  setEditPrevIndex(String(r.previous_index));
                                  setEditCurrIndex(String(r.current_index));
                                  setEditReadUnitPrice(String(r.unit_price));
                                  setEditReadingOpen(true);
                                }}
                                className="p-1.5 rounded-lg text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition"
                                title="Cập nhật chỉ số"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                            ) : (
                              <span className="text-[11px] text-slate-400">Đã chốt</span>
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
                Trang {readingsPage} / {readingsTotalPages} (Tổng {readingsTotal} bản ghi)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={readingsPage <= 1 || loadingReadings}
                  onClick={() => setReadingsPage((p) => Math.max(1, p - 1))}
                >
                  Trang trước
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={readingsPage >= readingsTotalPages || loadingReadings}
                  onClick={() => setReadingsPage((p) => Math.min(readingsTotalPages, p + 1))}
                >
                  Trang sau
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: INVOICES */}
      {activeTab === 'invoices' && (
        <div className="space-y-4 no-print">
          {invoicesError && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
                <span>{invoicesError}</span>
              </div>
              <Button size="sm" variant="outline" onClick={loadInvoices}>
                Thử lại
              </Button>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-2xl border border-slate-200">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Kỳ thu</label>
              <select
                value={invPeriodFilter}
                onChange={(e) => {
                  setInvPeriodFilter(e.target.value);
                  setInvoicesPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả kỳ thu</option>
                {allPeriods.map((p) => (
                  <option key={p.id} value={String(p.id)}>
                    {p.name} ({p.period_month})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Hộ gia đình</label>
              <select
                value={invHouseholdFilter}
                onChange={(e) => {
                  setInvHouseholdFilter(e.target.value);
                  setInvoicesPage(1);
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
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Trạng thái nộp phí</label>
              <select
                value={invStatusFilter}
                onChange={(e) => {
                  setInvStatusFilter(e.target.value);
                  setInvoicesPage(1);
                }}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="ALL">Tất cả trạng thái</option>
                <option value="UNPAID">Chưa nộp</option>
                <option value="PARTIAL">Nộp một phần</option>
                <option value="PAID">Đã nộp đủ</option>
              </select>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Số phiếu</th>
                    <th className="py-3 px-4">Kỳ thu</th>
                    <th className="py-3 px-4">Hộ / Căn hộ</th>
                    <th className="py-3 px-4 text-right">Phí phát sinh</th>
                    <th className="py-3 px-4 text-right">Miễn giảm</th>
                    <th className="py-3 px-4 text-right">Tổng phải nộp</th>
                    <th className="py-3 px-4 text-right">Đã nộp</th>
                    <th className="py-3 px-4 text-center">Trạng thái</th>
                    <th className="py-3 px-4 text-right">Chi tiết</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invoices.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-slate-400">
                        {loadingInvoices
                          ? 'Đang tải danh sách giấy báo nộp phí...'
                          : 'Chưa có giấy báo nộp phí nào.'}
                      </td>
                    </tr>
                  ) : (
                    invoices.map((inv) => {
                      const period = inv.billing_period_id
                        ? periodMap.get(inv.billing_period_id)
                        : null;
                      return (
                        <tr key={inv.id} className="hover:bg-slate-50">
                          <td className="py-3.5 px-4 font-mono font-bold text-slate-800">
                            #{inv.id}
                          </td>
                          <td className="py-3.5 px-4 text-slate-700">
                            {period
                              ? period.name
                              : inv.billing_period_id
                              ? `Kỳ #${inv.billing_period_id}`
                              : '---'}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="font-mono font-bold text-blue-700">
                              {inv.household_code}
                            </span>
                            {inv.apartment_code && (
                              <span className="ml-1.5 bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono text-[11px]">
                                {inv.apartment_code} ({inv.apartment_area}m²)
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-slate-700">
                            {formatVND(inv.fee_amount)}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-emerald-700">
                            {inv.discount_amount > 0
                              ? `-${formatVND(inv.discount_amount)}`
                              : '0 đ'}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900">
                            {formatVND(inv.total_due)}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-slate-600">
                            {formatVND(inv.paid_amount)}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            {getInvoiceStatusBadge(inv.status)}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={() => handleOpenInvoice(inv.id)}
                              disabled={loadingInvoiceDetail}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 p-1 rounded transition"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>Xem & In</span>
                            </button>
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
                Trang {invoicesPage} / {invoicesTotalPages} (Tổng {invoicesTotal} giấy báo phí)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={invoicesPage <= 1 || loadingInvoices}
                  onClick={() => setInvoicesPage((p) => Math.max(1, p - 1))}
                >
                  Trang trước
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={invoicesPage >= invoicesTotalPages || loadingInvoices}
                  onClick={() => setInvoicesPage((p) => Math.min(invoicesTotalPages, p + 1))}
                >
                  Trang sau
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Tạo kỳ thu mới */}
      <Modal
        isOpen={createPeriodOpen}
        onClose={() => setCreatePeriodOpen(false)}
        title="Tạo kỳ thu phí mới"
        description="Khởi tạo kỳ tính phí hàng tháng (ngày bắt đầu kỳ thu mặc định là ngày 01 của tháng)."
      >
        <form onSubmit={handleCreatePeriod} className="space-y-4">
          <Input
            label="Tháng tính phí"
            type="month"
            value={newMonth}
            onChange={(e) => handleMonthChange(e.target.value)}
            required
          />

          <Input
            label="Tên kỳ thu"
            placeholder="Ví dụ: Kỳ thu tháng 11/2026"
            value={newPeriodName}
            onChange={(e) => setNewPeriodName(e.target.value)}
            required
          />

          <Input
            label="Hạn thanh toán (Tùy chọn)"
            type="date"
            min={newMonth ? `${newMonth}-01` : undefined}
            value={newDueDate}
            onChange={(e) => setNewDueDate(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setCreatePeriodOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit" isLoading={creatingPeriod}>
              Khởi tạo kỳ thu
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Chi tiết kỳ thu */}
      {periodDetail && (
        <Modal
          isOpen={true}
          onClose={() => setPeriodDetail(null)}
          title={`Thông tin kỳ thu: ${periodDetail.name}`}
          description={`Mã kỳ #${periodDetail.id}`}
        >
          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3 p-4 bg-slate-50 border border-slate-200 rounded-2xl">
              <div>
                <span className="text-slate-400 block">Tháng áp dụng</span>
                <span className="font-mono font-bold text-slate-900">
                  {periodDetail.period_month}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">Trạng thái</span>
                <div className="mt-0.5">{getPeriodStatusBadge(periodDetail.status)}</div>
              </div>
              <div>
                <span className="text-slate-400 block">Hạn thanh toán</span>
                <span className="font-mono text-slate-800">{periodDetail.due_date || '---'}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Thời điểm tính phí</span>
                <span className="font-mono text-slate-800">
                  {periodDetail.generated_at
                    ? new Date(periodDetail.generated_at).toLocaleString('vi-VN')
                    : 'Chưa chạy'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">Thời điểm chốt kỳ</span>
                <span className="font-mono text-slate-800">
                  {periodDetail.closed_at
                    ? new Date(periodDetail.closed_at).toLocaleString('vi-VN')
                    : 'Chưa chốt'}
                </span>
              </div>
            </div>
            <div className="flex justify-end">
              <Button variant="primary" size="sm" onClick={() => setPeriodDetail(null)}>
                Đóng
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Kết quả chạy tính phí tự động */}
      {generateResult && (
        <Modal
          isOpen={true}
          onClose={() => setGenerateResult(null)}
          title="Kết quả tính phí tự động"
          description={`Kỳ thu: ${generateResult.period.name}`}
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start gap-3 text-emerald-900">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Hoàn tất tính phí & lập giấy báo nộp tiền!</p>
                <p className="mt-0.5 text-emerald-800">
                  Đơn giá và chính sách miễn giảm tại thời điểm kỳ thu đã được lưu cố định trên từng dòng giấy báo.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <p className="text-slate-500 text-[11px]">Số hộ xử lý</p>
                <p className="text-lg font-bold font-mono text-slate-900 mt-0.5">
                  {generateResult.result.households_processed}
                </p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <p className="text-slate-500 text-[11px]">Giấy báo đã tạo</p>
                <p className="text-lg font-bold font-mono text-blue-700 mt-0.5">
                  {generateResult.result.invoices_created}
                </p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <p className="text-slate-500 text-[11px]">Tổng số tiền</p>
                <p className="text-sm font-bold font-mono text-emerald-700 mt-1">
                  {formatVND(generateResult.result.total_fee_amount)}
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setGenerateResult(null)}>
                Đóng
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setInvPeriodFilter(String(generateResult.period.id));
                  setInvoicesPage(1);
                  setGenerateResult(null);
                  setActiveTab('invoices');
                }}
              >
                Xem danh sách giấy báo phí
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Nhập chỉ số công tơ */}
      <Modal
        isOpen={addReadingOpen}
        onClose={() => setAddReadingOpen(false)}
        title="Nhập chỉ số Điện / Nước"
        description="Ghi nhận chỉ số tiêu thụ cho hộ gia đình trong kỳ thu chưa chốt."
      >
        <form onSubmit={handleAddReading} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Kỳ thu <span className="text-rose-500">*</span>
            </label>
            <select
              value={readPeriodId}
              onChange={(e) => setReadPeriodId(e.target.value ? Number(e.target.value) : '')}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              <option value="">-- Chọn kỳ thu chưa chốt --</option>
              {allPeriods
                .filter((p) => p.status !== 'CLOSED')
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.period_month})
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Hộ gia đình <span className="text-rose-500">*</span>
            </label>
            <select
              value={readHouseholdId}
              onChange={(e) => setReadHouseholdId(e.target.value ? Number(e.target.value) : '')}
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
              Khoản thu theo chỉ số <span className="text-rose-500">*</span>
            </label>
            <select
              value={readFeeTypeId}
              onChange={(e) => setReadFeeTypeId(e.target.value ? Number(e.target.value) : '')}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            >
              <option value="">-- Chọn khoản thu công tơ --</option>
              {meteredFees.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.code} - {f.name} (
                  {f.current_unit_price !== null && f.current_unit_price !== undefined
                    ? `${formatVND(f.current_unit_price)}/${f.unit_label}`
                    : 'Chưa có đơn giá'}
                  )
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Chỉ số cũ"
              type="number"
              step="any"
              min="0"
              value={prevIndex}
              onChange={(e) => setPrevIndex(e.target.value)}
              required
            />
            <Input
              label="Chỉ số mới"
              type="number"
              step="any"
              min={prevIndex || '0'}
              value={currIndex}
              onChange={(e) => setCurrIndex(e.target.value)}
              required
            />
          </div>

          {previewConsumption !== null && (
            <div className="p-2.5 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-900 flex justify-between">
              <span>Sản lượng tiêu thụ dự kiến:</span>
              <span className="font-mono font-bold">{previewConsumption}</span>
            </div>
          )}

          <Input
            label="Đơn giá áp dụng riêng (VNĐ - Tùy chọn)"
            type="number"
            min="0"
            step="1"
            placeholder="Để trống để tự động lấy đơn giá theo biểu phí hiện hành"
            value={readUnitPrice}
            onChange={(e) => setReadUnitPrice(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setAddReadingOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu chỉ số
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Sửa chỉ số công tơ */}
      <Modal
        isOpen={editReadingOpen}
        onClose={() => setEditReadingOpen(false)}
        title={`Cập nhật chỉ số — Hộ ${editReadingTarget?.household_code || ''}`}
        description={editReadingTarget ? `${editReadingTarget.fee_name}` : undefined}
      >
        <form onSubmit={handleEditReading} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Chỉ số cũ"
              type="number"
              step="any"
              min="0"
              value={editPrevIndex}
              onChange={(e) => setEditPrevIndex(e.target.value)}
              required
            />
            <Input
              label="Chỉ số mới"
              type="number"
              step="any"
              min={editPrevIndex || '0'}
              value={editCurrIndex}
              onChange={(e) => setEditCurrIndex(e.target.value)}
              required
            />
          </div>

          <Input
            label="Đơn giá (VNĐ)"
            type="number"
            min="0"
            step="1"
            value={editReadUnitPrice}
            onChange={(e) => setEditReadUnitPrice(e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setEditReadingOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" type="submit">
              Lưu thay đổi
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Chi tiết & In Giấy báo nộp phí (US-17, US-47) */}
      {invoiceDetail && (() => {
        const invoicePrintSheet = (
          <div className="printable-area bg-white p-4 sm:p-6 border border-slate-200 rounded-2xl space-y-5 text-xs print:border-0 print:rounded-none print:p-0">
            {/* Printable Header */}
            <div className="flex items-start justify-between border-b border-slate-200 pb-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-blue-700">
                  Ban Quản Lý Chung Cư BlueMoon
                </p>
                <h2 className="text-lg font-extrabold text-slate-900 mt-0.5">
                  GIẤY BÁO NỘP PHÍ DỊCH VỤ
                </h2>
                <p className="text-slate-500 mt-0.5">
                  Số phiếu: <span className="font-mono font-bold">#{invoiceDetail.id}</span>
                  {invoiceDetail.billing_period_id && periodMap.get(invoiceDetail.billing_period_id)
                    ? ` • ${periodMap.get(invoiceDetail.billing_period_id)?.name}`
                    : ''}
                </p>
              </div>
              <div className="text-right">
                {getInvoiceStatusBadge(invoiceDetail.status)}
                {periodMap.get(invoiceDetail.billing_period_id || -1)?.due_date && (
                  <p className="text-[11px] text-slate-500 mt-1">
                    Hạn nộp:{' '}
                    <span className="font-mono font-semibold">
                      {periodMap.get(invoiceDetail.billing_period_id || -1)?.due_date}
                    </span>
                  </p>
                )}
              </div>
            </div>

            {/* Household Info */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div>
                <span className="text-slate-400 block text-[11px]">Mã hộ gia đình</span>
                <span className="font-mono font-bold text-slate-900">
                  {invoiceDetail.household_code}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Căn hộ</span>
                <span className="font-semibold text-slate-900">
                  {invoiceDetail.apartment_code || '---'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Diện tích</span>
                <span className="font-mono font-semibold text-slate-900">
                  {invoiceDetail.apartment_area} m²
                </span>
              </div>
            </div>

            {/* Breakdown Items Table */}
            <div className="border border-slate-200 rounded-xl overflow-hidden print:overflow-visible">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold text-[11px] uppercase">
                  <tr>
                    <th className="py-2.5 px-3">STT</th>
                    <th className="py-2.5 px-3">Khoản thu</th>
                    <th className="py-2.5 px-3 text-right">SL</th>
                    <th className="py-2.5 px-3 text-right">Đơn giá</th>
                    <th className="py-2.5 px-3 text-right">Thành tiền</th>
                    <th className="py-2.5 px-3 text-right">Miễn giảm</th>
                    <th className="py-2.5 px-3 text-right">Phải nộp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invoiceDetail.items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-4 text-center text-slate-400">
                        Không có dòng chi tiết khoản thu.
                      </td>
                    </tr>
                  ) : (
                    invoiceDetail.items.map((item, idx) => (
                      <tr key={item.id}>
                        <td className="py-2.5 px-3 font-mono text-slate-500">{idx + 1}</td>
                        <td className="py-2.5 px-3">
                          <p className="font-semibold text-slate-900">{item.fee_name}</p>
                          {item.description && (
                            <p className="text-[11px] text-slate-500">{item.description}</p>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                          {item.quantity}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                          {formatVND(item.unit_price)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                          {formatVND(item.gross_amount)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-emerald-700">
                          {item.discount_amount > 0
                            ? `-${formatVND(item.discount_amount)}`
                            : '0 đ'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                          {formatVND(item.net_amount)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Financial Summary */}
            <div className="flex justify-end">
              <div className="w-full sm:w-80 space-y-1.5 p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <div className="flex justify-between text-slate-600">
                  <span>Tổng phí phát sinh:</span>
                  <span className="font-mono font-semibold">
                    {formatVND(invoiceDetail.fee_amount)}
                  </span>
                </div>
                <div className="flex justify-between text-emerald-700">
                  <span>Tổng miễn giảm:</span>
                  <span className="font-mono font-semibold">
                    -{formatVND(invoiceDetail.discount_amount)}
                  </span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Nợ kỳ trước chuyển sang:</span>
                  <span className="font-mono">{formatVND(invoiceDetail.previous_debt)}</span>
                </div>
                <div className="flex justify-between text-blue-700">
                  <span>Khấu trừ số dư ứng trước:</span>
                  <span className="font-mono">-{formatVND(invoiceDetail.credit_applied)}</span>
                </div>
                <div className="flex justify-between text-sm font-extrabold text-slate-900 pt-2 border-t border-slate-200">
                  <span>Tổng cộng phải thanh toán:</span>
                  <span className="font-mono text-blue-700">
                    {formatVND(invoiceDetail.total_due)}
                  </span>
                </div>
                <div className="flex justify-between text-slate-600 pt-1">
                  <span>Đã thanh toán:</span>
                  <span className="font-mono font-semibold text-emerald-700">
                    {formatVND(invoiceDetail.paid_amount)}
                  </span>
                </div>
                <div className="flex justify-between font-bold text-rose-700">
                  <span>Còn lại cần nộp:</span>
                  <span className="font-mono">
                    {formatVND(Math.max(0, invoiceDetail.total_due - invoiceDetail.paid_amount))}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

        return (
          <>
            <Modal
              isOpen={true}
              onClose={() => setInvoiceDetail(null)}
              size="xl"
              title={`Giấy báo nộp phí #${invoiceDetail.id}`}
              description={`Hộ ${invoiceDetail.household_code} ${invoiceDetail.apartment_code ? `• Căn hộ ${invoiceDetail.apartment_code}` : ''}`}
            >
              <div className="space-y-4">
                {invoicePrintSheet}

                <div className="flex justify-end gap-2 no-print">
                  <Button variant="outline" onClick={() => setInvoiceDetail(null)}>
                    Đóng
                  </Button>
                  <Button
                    variant="primary"
                    onClick={() => window.print()}
                    icon={<Printer className="w-4 h-4" />}
                  >
                    In giấy báo phí
                  </Button>
                </div>
              </div>
            </Modal>

            {createPortal(
              <div className="print-portal-root" aria-hidden="true">
                {invoicePrintSheet}
              </div>,
              document.body
            )}
          </>
        );
      })()}
    </div>
  );
};
