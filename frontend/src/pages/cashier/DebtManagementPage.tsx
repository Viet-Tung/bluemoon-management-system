import React, { useEffect, useState } from 'react';
import {
  History,
  Search,
  Ban,
  Printer,
  AlertCircle,
  FileText,
  Eye,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { Payment } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { WatermarkReceipt } from '../../components/common/WatermarkReceipt';
import { useToast } from '../../context/ToastContext';

export const DebtManagementPage: React.FC = () => {
  const { success, error } = useToast();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Cancel Modal (US-22)
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [paymentToCancel, setPaymentToCancel] = useState<Payment | null>(null);
  const [cancelReason, setCancelReason] = useState('');

  // View Receipt Modal
  const [viewPayment, setViewPayment] = useState<Payment | null>(null);

  useEffect(() => {
    loadPayments();
  }, []);

  const loadPayments = async () => {
    try {
      const data = await ApiClient.getPayments();
      setPayments(data);
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleCancelPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!paymentToCancel) return;
    if (!cancelReason.trim()) {
      error('Bắt buộc phải nhập lý do hủy giao dịch (AC-22.1).');
      return;
    }

    try {
      await ApiClient.cancelPayment(paymentToCancel.id, cancelReason);
      success(
        `Đã hủy thành công biên lai #${paymentToCancel.receipt_no}! Công nợ đã được hoàn trả lại cho hộ và ghi log kiểm toán (US-22).`
      );
      setCancelModalOpen(false);
      setCancelReason('');
      loadPayments();
    } catch (err: any) {
      error(err.message);
    }
  };

  const filtered = payments.filter((p) => {
    const matchSearch =
      p.receipt_no.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.apartment_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.payer_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchStatus = statusFilter === 'ALL' || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <History className="w-6 h-6 text-blue-600" />
          <span>Theo dõi Giao dịch & Hủy Biên lai Sai sót (US-21, US-22)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Quản lý lịch sử nộp tiền; hỗ trợ chức năng hủy biên lai sai sót kèm lý do bắt buộc, khôi phục lại công nợ và lưu vết kiểm toán bất biến (AC-22.1).
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-center gap-3">
        <div className="flex-1 w-full">
          <Input
            placeholder="Tìm theo số biên lai (BL00000001), mã căn hộ, hoặc tên người nộp..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search className="w-4 h-4" />}
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">Tình trạng:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full sm:w-36 bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="ALL">Tất cả biên lai</option>
            <option value="VALID">Hợp lệ</option>
            <option value="CANCELLED">Đã hủy</option>
          </select>
        </div>
      </div>

      {/* Payments Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3.5 px-4">Số Biên Lai</th>
                <th className="py-3.5 px-4">Căn hộ / Hộ</th>
                <th className="py-3.5 px-4">Người nộp tiền</th>
                <th className="py-3.5 px-4">Thời gian</th>
                <th className="py-3.5 px-4">Hình thức</th>
                <th className="py-3.5 px-4 text-right">Tổng tiền thu</th>
                <th className="py-3.5 px-4 text-center">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-bold text-blue-700 flex items-center gap-1.5">
                    <span>{p.receipt_no}</span>
                    {p.print_count > 1 && (
                      <span className="bg-red-50 text-red-600 text-[10px] font-bold px-1 rounded border border-red-200">
                        Bản sao
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-800">
                    Căn {p.apartment_code} ({p.household_code})
                  </td>
                  <td className="py-3.5 px-4 text-slate-700">{p.payer_name}</td>
                  <td className="py-3.5 px-4 text-slate-600">
                    {new Date(p.paid_at).toLocaleDateString('vi-VN')} {new Date(p.paid_at).toLocaleTimeString('vi-VN')}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md font-medium">
                      {p.method === 'CASH' ? 'Tiền mặt' : 'Chuyển khoản'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900 text-sm">
                    {formatVND(p.amount)}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <Badge variant={p.status === 'VALID' ? 'success' : 'danger'} dot>
                      {p.status === 'VALID' ? 'Hợp lệ' : 'Đã hủy'}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setViewPayment(p)}
                      icon={<Eye className="w-3.5 h-3.5" />}
                    >
                      Xem / In
                    </Button>
                    {p.status === 'VALID' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-rose-600 hover:bg-rose-50"
                        onClick={() => {
                          setPaymentToCancel(p);
                          setCancelModalOpen(true);
                        }}
                        icon={<Ban className="w-3.5 h-3.5" />}
                      >
                        Hủy biên lai
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal View & Print Receipt */}
      {viewPayment && (
        <Modal
          isOpen={!!viewPayment}
          onClose={() => setViewPayment(null)}
          title={`Chi tiết Biên lai #${viewPayment.receipt_no}`}
          size="xl"
        >
          <WatermarkReceipt
            payment={viewPayment}
            onPrint={async () => {
              const count = await ApiClient.recordPrintCount(viewPayment.id);
              setViewPayment({ ...viewPayment, print_count: count });
              loadPayments();
            }}
          />
        </Modal>
      )}

      {/* Modal Cancel Payment (US-22) */}
      {paymentToCancel && (
        <Modal
          isOpen={cancelModalOpen}
          onClose={() => setCancelModalOpen(false)}
          title={`Hủy Biên lai #${paymentToCancel.receipt_no} (US-22)`}
          description="Hệ thống không xóa vật lý giao dịch; biên lai sẽ chuyển trạng thái Đã hủy, hoàn trả lại công nợ cũ cho hộ và lưu vết Audit Log (AC-22.1)."
        >
          <form onSubmit={handleCancelPayment} className="space-y-4">
            <div className="bg-rose-50 p-3.5 rounded-xl border border-rose-200 text-xs text-rose-900 space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-rose-600" />
                <span>Cảnh báo hoàn tác công nợ:</span>
              </p>
              <p>Biên lai: <strong>{paymentToCancel.receipt_no}</strong> - Căn: <strong>{paymentToCancel.apartment_code}</strong></p>
              <p>Số tiền hoàn trả lại vào công nợ: <strong>{formatVND(paymentToCancel.allocated_amount)}</strong></p>
            </div>

            <Input
              label="Lý do hủy biên lai (Bắt buộc nhập theo AC-22.1)"
              placeholder="Ví dụ: Thu nhầm hộ, nhập sai số tiền, cư dân yêu cầu đổi sang chuyển khoản..."
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              required
            />

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button variant="outline" type="button" onClick={() => setCancelModalOpen(false)}>
                Đóng
              </Button>
              <Button variant="danger" type="submit">
                Xác nhận hủy biên lai
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
