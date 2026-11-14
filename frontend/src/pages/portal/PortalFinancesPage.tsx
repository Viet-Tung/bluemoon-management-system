import React, { useEffect, useState } from 'react';
import {
  CreditCard,
  Receipt,
  Download,
  Eye,
  CheckCircle,
  AlertCircle,
  Printer,
  Sparkles,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { Invoice, Payment } from '../../types';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { WatermarkReceipt } from '../../components/common/WatermarkReceipt';
import { useToast } from '../../context/ToastContext';

export const PortalFinancesPage: React.FC = () => {
  const { error } = useToast();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [viewReceipt, setViewReceipt] = useState<Payment | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const invs = await ApiClient.getInvoices();
      // Resident B1204 only sees household_id 1
      setInvoices(invs.filter((i) => i.household_id === 1));

      const pmts = await ApiClient.getPayments();
      setPayments(pmts.filter((p) => p.household_id === 1));
    } catch (err: any) {
      error(err.message);
    }
  };

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  const currentInvoice = invoices[0];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md">
          Cổng Tra Cứu Tài Chính
        </span>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
          <CreditCard className="w-6 h-6 text-blue-600" />
          <span>Tra cứu Công nợ & Lịch sử Nộp phí Căn B1204 (US-35)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Theo dõi minh bạch các khoản phí phát sinh hàng tháng, số dư có hiện tại và tải biên lai điện tử có chữ ký số.
        </p>
      </div>

      {/* Financial Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
          <p className="text-xs text-slate-500 font-medium">Hạn thanh toán kỳ này</p>
          <p className="text-xl font-bold text-slate-800 mt-1">20/11/2026</p>
          <p className="text-xs text-amber-600 mt-1 flex items-center gap-1 font-semibold">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Còn 5 ngày để thanh toán</span>
          </p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
          <p className="text-xs text-slate-500 font-medium">Số dư có lũy kế (Credit Balance)</p>
          <p className="text-2xl font-bold font-mono text-emerald-600 mt-1">50.000 đ</p>
          <p className="text-xs text-emerald-700 mt-1">Đã cấn trừ trực tiếp vào hóa đơn kỳ này</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
          <p className="text-xs text-slate-500 font-medium">Tổng tiền cần thanh toán</p>
          <p className="text-2xl font-bold font-mono text-blue-700 mt-1">
            {currentInvoice ? formatVND(currentInvoice.total_due) : '0 đ'}
          </p>
          <Badge variant={currentInvoice?.status.toLowerCase() as any} size="sm" className="mt-1">
            {currentInvoice?.status === 'PAID' ? 'Đã nộp đủ' : 'Chưa thanh toán'}
          </Badge>
        </div>
      </div>

      {/* Itemized Fee Breakdown for current month */}
      {currentInvoice && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                Chi tiết Giấy báo nộp phí ({currentInvoice.period_name})
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Căn hộ B1204 • Diện tích: {currentInvoice.apartment_area} m²
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              icon={<Printer className="w-3.5 h-3.5" />}
              onClick={() => window.print()}
            >
              In giấy báo nộp phí
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Khoản thu</th>
                  <th className="py-3 px-4">Số lượng / Chỉ số</th>
                  <th className="py-3 px-4 text-right">Đơn giá</th>
                  <th className="py-3 px-4 text-right">Thành tiền (VNĐ)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {currentInvoice.items.map((item) => (
                  <tr key={item.id}>
                    <td className="py-3 px-4 font-semibold text-slate-800">
                      {item.fee_name}
                      {item.description && (
                        <span className="block text-[11px] text-slate-400 font-normal">
                          {item.description}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-mono">{item.quantity}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-700">
                      {formatVND(item.unit_price)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                      {formatVND(item.net_amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Math calculation box */}
          <div className="bg-slate-50 p-4 border-t border-slate-200 text-xs text-right space-y-1.5 font-mono">
            <div className="flex justify-between">
              <span className="text-slate-500 font-sans">Tổng phí kỳ này:</span>
              <span className="font-semibold">{formatVND(currentInvoice.fee_amount)}</span>
            </div>
            {currentInvoice.credit_applied > 0 && (
              <div className="flex justify-between text-amber-700">
                <span className="font-sans">Khấu trừ số dư có nộp thừa:</span>
                <span>-{formatVND(currentInvoice.credit_applied)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm font-bold border-t border-slate-200 pt-2 text-blue-900 font-sans">
              <span>SỐ TIỀN CẦN THANH TOÁN:</span>
              <span className="font-mono text-base">{formatVND(currentInvoice.total_due)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Payment History & Printable Receipts */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Lịch sử biên lai đã thanh toán</h3>
            <p className="text-xs text-slate-500 mt-0.5">Biên lai điện tử có giá trị pháp lý lưu trữ</p>
          </div>
        </div>

        {payments.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            Chưa có biên lai thanh toán nào được ghi nhận cho căn B1204
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Số Biên Lai</th>
                  <th className="py-3 px-4">Ngày nộp</th>
                  <th className="py-3 px-4">Hình thức</th>
                  <th className="py-3 px-4 text-right">Số tiền nộp</th>
                  <th className="py-3 px-4 text-center">Trạng thái</th>
                  <th className="py-3 px-4 text-right">Biên lai điện tử</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {payments.map((p) => (
                  <tr key={p.id}>
                    <td className="py-3 px-4 font-mono font-bold text-blue-700">{p.receipt_no}</td>
                    <td className="py-3 px-4 text-slate-600">
                      {new Date(p.paid_at).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      {p.method === 'CASH' ? 'Tiền mặt tại quầy' : 'Chuyển khoản'}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                      {formatVND(p.amount)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant={p.status === 'VALID' ? 'success' : 'danger'} dot size="sm">
                        {p.status === 'VALID' ? 'Hợp lệ' : 'Đã hủy'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setViewReceipt(p)}
                        icon={<Eye className="w-3.5 h-3.5" />}
                      >
                        Tải / In biên lai
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal View Receipt */}
      {viewReceipt && (
        <Modal
          isOpen={!!viewReceipt}
          onClose={() => setViewReceipt(null)}
          title={`Biên lai thu tiền điện tử #${viewReceipt.receipt_no}`}
          size="xl"
        >
          <WatermarkReceipt
            payment={viewReceipt}
            onPrint={async () => {
              const newCount = await ApiClient.recordPrintCount(viewReceipt.id);
              setViewReceipt({ ...viewReceipt, print_count: newCount });
            }}
          />
        </Modal>
      )}
    </div>
  );
};
