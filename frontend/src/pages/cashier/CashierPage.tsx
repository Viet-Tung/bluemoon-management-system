import React, { useEffect, useState } from 'react';
import {
  CreditCard,
  Search,
  CheckSquare,
  Square,
  Banknote,
  Building,
  Printer,
  Sparkles,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { Invoice, InvoiceItem, Payment } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { WatermarkReceipt } from '../../components/common/WatermarkReceipt';
import { useToast } from '../../context/ToastContext';

export const CashierPage: React.FC = () => {
  const { success, error } = useToast();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);

  // Payment form states
  const [selectedItemIds, setSelectedItemIds] = useState<number[]>([]);
  const [receivedAmount, setReceivedAmount] = useState<number>(0);
  const [paymentMethod, setPaymentMethod] = useState<'CASH' | 'BANK_TRANSFER'>('CASH');
  const [referenceNo, setReferenceNo] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Receipt Modal
  const [completedPayment, setCompletedPayment] = useState<Payment | null>(null);

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async () => {
    try {
      const data = await ApiClient.getInvoices();
      setInvoices(data);
      if (data.length > 0 && !selectedInvoice) {
        selectInvoice(data[0]);
      }
    } catch (err: any) {
      error(err.message);
    }
  };

  const selectInvoice = (inv: Invoice) => {
    setSelectedInvoice(inv);
    // Default select all unpaid items
    const unpaidIds = inv.items
      .filter((it) => it.net_amount > it.paid_amount)
      .map((it) => it.id);
    setSelectedItemIds(unpaidIds);
    setReceivedAmount(inv.remaining_amount);
  };

  const toggleItem = (id: number) => {
    if (selectedItemIds.includes(id)) {
      setSelectedItemIds(selectedItemIds.filter((itemId) => itemId !== id));
    } else {
      setSelectedItemIds([...selectedItemIds, id]);
    }
  };

  const filteredInvoices = invoices.filter(
    (inv) =>
      inv.apartment_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.head_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.household_code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  // Calculation
  const selectedItemsTotal = (selectedInvoice?.items || [])
    .filter((it) => selectedItemIds.includes(it.id))
    .reduce((sum, it) => sum + (it.net_amount - it.paid_amount), 0);

  const overpayment = Math.max(0, receivedAmount - selectedItemsTotal);

  const handlePayment = async () => {
    if (!selectedInvoice) return;
    if (selectedItemIds.length === 0) {
      error('Vui lòng tích chọn ít nhất một khoản thu cần thanh toán.');
      return;
    }
    if (receivedAmount <= 0) {
      error('Số tiền khách đưa phải lớn hơn 0.');
      return;
    }
    if (receivedAmount < selectedItemsTotal) {
      error(`Số tiền khách đưa (${formatVND(receivedAmount)}) không đủ cho các khoản đã chọn (${formatVND(selectedItemsTotal)}). Hãy bỏ bớt tích chọn khoản phí.`);
      return;
    }

    setIsSubmitting(true);
    try {
      const payment = await ApiClient.collectPayment({
        household_id: selectedInvoice.household_id,
        amount: receivedAmount,
        method: paymentMethod,
        reference_no: referenceNo,
        item_ids: selectedItemIds,
      });

      success(`Gạch nợ thành công! Đã tạo biên lai số ${payment.receipt_no}`);
      setCompletedPayment(payment);
      loadInvoices();
    } catch (err: any) {
      error(err.message || 'Không thể ghi nhận thanh toán.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <CreditCard className="w-6 h-6 text-blue-600" />
          <span>Quầy Thu Ngân & Gạch Nợ Tự Động (US-18, US-19, US-20)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Tìm kiếm tức thì hộ gia đình (dưới 1 giây), hỗ trợ nộp đủ, nộp một phần theo khoản tích chọn, hoặc nộp thừa (tự động cộng vào số dư có credit).
        </p>
      </div>

      {/* Split-Screen Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Instant Search & Apartment List (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Tìm nhanh căn hộ / Chủ hộ (US-18)
            </label>
            <Input
              placeholder="Gõ mã căn (VD: B1204, A0502) hoặc tên chủ hộ..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="w-4 h-4 text-blue-600" />}
              autoFocus
            />
          </div>

          <div className="space-y-2 max-h-[580px] overflow-y-auto pr-1">
            {filteredInvoices.map((inv) => {
              const isSelected = selectedInvoice?.id === inv.id;
              return (
                <div
                  key={inv.id}
                  onClick={() => selectInvoice(inv)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50/60 shadow-xs'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-mono font-bold text-base text-blue-700">
                        Căn {inv.apartment_code}
                      </span>
                      <p className="text-xs font-semibold text-slate-800 mt-0.5">{inv.head_name}</p>
                      <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                        {inv.household_code} • {inv.apartment_area} m²
                      </p>
                    </div>
                    <div className="text-right">
                      <Badge variant={inv.status.toLowerCase() as any} size="sm">
                        {inv.status === 'PAID'
                          ? 'Đã nộp đủ'
                          : inv.status === 'PARTIAL'
                          ? 'Nộp 1 phần'
                          : 'Chưa nộp'}
                      </Badge>
                      <p className="text-xs font-mono font-bold text-slate-900 mt-2">
                        {formatVND(inv.remaining_amount)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Checkout Breakdown & Allocations (7 cols) */}
        {selectedInvoice ? (
          <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
            {/* Resident Card Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-[11px] font-bold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md uppercase">
                  Đang thu tiền cho căn {selectedInvoice.apartment_code}
                </span>
                <h2 className="text-lg font-bold text-slate-900 mt-2">{selectedInvoice.head_name}</h2>
                <p className="text-xs text-slate-500 font-mono">
                  SĐT: {selectedInvoice.contact_phone || '---'} • Kỳ thu: {selectedInvoice.period_name}
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-400">Còn phải nộp kỳ này</span>
                <p className="text-xl font-bold font-mono text-rose-600 mt-0.5">
                  {formatVND(selectedInvoice.remaining_amount)}
                </p>
              </div>
            </div>

            {/* Itemized Selection Table (AC-19.2) */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Chọn các khoản cần gạch nợ (AC-19.2)
                </p>
                <span className="text-xs text-slate-500">Tích chọn để thanh toán từng phần</span>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
                {selectedInvoice.items.map((item) => {
                  const isChecked = selectedItemIds.includes(item.id);
                  const isPaid = item.paid_amount >= item.net_amount;
                  const remaining = item.net_amount - item.paid_amount;

                  return (
                    <div
                      key={item.id}
                      onClick={() => !isPaid && toggleItem(item.id)}
                      className={`p-3.5 flex items-center justify-between text-xs transition-colors ${
                        isPaid
                          ? 'bg-slate-50 opacity-60 cursor-not-allowed'
                          : isChecked
                          ? 'bg-blue-50/40 cursor-pointer'
                          : 'hover:bg-slate-50 cursor-pointer'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {isPaid ? (
                          <div className="w-4 h-4 rounded text-emerald-600 flex items-center justify-center font-bold">
                            ✓
                          </div>
                        ) : isChecked ? (
                          <CheckSquare className="w-4 h-4 text-blue-600 flex-shrink-0" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        )}
                        <div>
                          <p className="font-semibold text-slate-800">{item.fee_name}</p>
                          <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                            {item.description || `${item.quantity} ${item.fee_group}`}
                          </p>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="font-mono font-bold text-slate-900">
                          {formatVND(remaining)}
                        </span>
                        {isPaid && (
                          <span className="block text-[10px] text-emerald-600 font-semibold">
                            Đã thanh toán
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Payment Details Input */}
            <div className="bg-slate-50 p-4 rounded-xl space-y-4 border border-slate-200">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Hình thức thanh toán
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setPaymentMethod('CASH')}
                      className={`py-2 px-3 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1.5 transition ${
                        paymentMethod === 'CASH'
                          ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                          : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                      }`}
                    >
                      <Banknote className="w-4 h-4" />
                      <span>Tiền mặt</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setPaymentMethod('BANK_TRANSFER')}
                      className={`py-2 px-3 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1.5 transition ${
                        paymentMethod === 'BANK_TRANSFER'
                          ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                          : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                      }`}
                    >
                      <Building className="w-4 h-4" />
                      <span>Chuyển khoản</span>
                    </button>
                  </div>
                </div>

                {paymentMethod === 'BANK_TRANSFER' ? (
                  <Input
                    label="Mã giao dịch ngân hàng"
                    placeholder="VD: FT26110098..."
                    value={referenceNo}
                    onChange={(e) => setReferenceNo(e.target.value)}
                  />
                ) : (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                      Ghi nhận quầy
                    </label>
                    <p className="text-xs text-slate-500 py-2">Thủ quỹ nhận tiền mặt tại văn phòng</p>
                  </div>
                )}
              </div>

              {/* Amount Inputs & Overpayment calculation */}
              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-200">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Tổng tiền các khoản đã chọn:
                  </label>
                  <p className="text-base font-bold font-mono text-blue-700 py-1">
                    {formatVND(selectedItemsTotal)}
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Số tiền khách đưa (VNĐ):
                  </label>
                  <input
                    type="number"
                    step="1000"
                    min="0"
                    value={receivedAmount}
                    onChange={(e) => setReceivedAmount(Number(e.target.value))}
                    className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-base font-mono font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Overpayment Alert (AC-19.5) */}
              {overpayment > 0 && (
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-900 text-xs flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-600" />
                    <span>Khách nộp thừa tiền (AC-19.5):</span>
                  </span>
                  <span className="font-mono font-bold text-sm">
                    +{formatVND(overpayment)} (Tự động cộng vào số dư có kỳ sau)
                  </span>
                </div>
              )}
            </div>

            {/* Confirm Payment Button */}
            <Button
              onClick={handlePayment}
              variant="primary"
              size="lg"
              className="w-full"
              isLoading={isSubmitting}
              icon={<ArrowRight className="w-5 h-5" />}
            >
              Xác nhận thu tiền & Sinh biên lai điện tử
            </Button>
          </div>
        ) : (
          <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
            Chọn một căn hộ ở danh sách bên trái để bắt đầu thu tiền
          </div>
        )}
      </div>

      {/* Modal View & Print Electronic Receipt (US-20, AC-20.2) */}
      {completedPayment && (
        <Modal
          isOpen={!!completedPayment}
          onClose={() => setCompletedPayment(null)}
          title={`Biên lai thu tiền điện tử #${completedPayment.receipt_no}`}
          size="xl"
        >
          <WatermarkReceipt
            payment={completedPayment}
            onPrint={async () => {
              const newCount = await ApiClient.recordPrintCount(completedPayment.id);
              setCompletedPayment({ ...completedPayment, print_count: newCount });
            }}
          />
        </Modal>
      )}
    </div>
  );
};
