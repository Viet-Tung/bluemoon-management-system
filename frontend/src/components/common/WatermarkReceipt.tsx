import React from 'react';
import { Payment } from '../../types';
import { Printer } from 'lucide-react';
import { Button } from './Button';

interface WatermarkReceiptProps {
  payment: Payment;
  onPrint?: () => void;
}

export const WatermarkReceipt: React.FC<WatermarkReceiptProps> = ({ payment, onPrint }) => {
  const isReprint = payment.print_count > 1;
  const isCancelled = payment.status === 'CANCELLED';

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  const handlePrint = () => {
    if (onPrint) onPrint();
    window.print();
  };

  return (
    <div className="relative bg-white border border-slate-300 rounded-2xl p-8 max-w-2xl mx-auto shadow-sm text-slate-800 printable-area overflow-hidden">
      {/* Dynamic Watermark Stamp for Reprint (AC-20.2) */}
      {isReprint && !isCancelled && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 select-none">
          <div className="border-4 border-red-500/30 text-red-500/30 text-6xl font-black tracking-widest uppercase px-12 py-4 rounded-3xl transform -rotate-25">
            BẢN SAO
          </div>
        </div>
      )}

      {/* Dynamic Watermark Stamp for Cancelled Receipt (AC-22.1) */}
      {isCancelled && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10 select-none">
          <div className="border-4 border-rose-600/40 text-rose-600/40 text-5xl font-black tracking-widest uppercase px-8 py-3 rounded-2xl transform -rotate-20 text-center">
            ĐÃ HỦY GIAO DỊCH
          </div>
          {payment.cancel_reason && (
            <p className="text-rose-600/60 font-semibold text-sm mt-2 transform -rotate-20">
              Lý do: {payment.cancel_reason}
            </p>
          )}
        </div>
      )}

      {/* Header with BlueMoon branding */}
      <div className="flex items-start justify-between border-b border-slate-200 pb-4 mb-6">
        <div>
          <h2 className="text-lg font-bold text-blue-900 tracking-tight">
            BAN QUẢN TRỊ CHUNG CƯ BLUEMOON
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">Số 1 Đại Cồ Việt, Hai Bà Trưng, Hà Nội</p>
          <p className="text-xs text-slate-500">Hotline: 1900 6868 | Email: bqt@bluemoon.vn</p>
        </div>
        <div className="text-right">
          <span className="text-xs font-semibold uppercase text-slate-400 block tracking-wider">
            Mẫu: DOC-02
          </span>
          <span className="text-sm font-mono font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-lg inline-block mt-1">
            {payment.receipt_no}
          </span>
          {isReprint && (
            <span className="text-[10px] text-red-600 font-bold block mt-1">
              (In lần thứ {payment.print_count})
            </span>
          )}
        </div>
      </div>

      {/* Title */}
      <div className="text-center my-4">
        <h1 className="text-xl font-bold uppercase tracking-wide text-slate-900">
          BIÊN LAI THU PHÍ ĐIỆN TỬ
        </h1>
        <p className="text-xs text-slate-500 italic mt-1">
          Ngày {new Date(payment.paid_at).toLocaleDateString('vi-VN')} -{' '}
          {new Date(payment.paid_at).toLocaleTimeString('vi-VN')}
        </p>
      </div>

      {/* Resident & Apartment Details */}
      <div className="grid grid-cols-2 gap-4 text-xs bg-slate-50 p-4 rounded-xl mb-6">
        <div>
          <span className="text-slate-500">Căn hộ:</span>{' '}
          <strong className="text-slate-900 text-sm">{payment.apartment_code}</strong>
        </div>
        <div>
          <span className="text-slate-500">Mã hộ gia đình:</span>{' '}
          <strong className="text-slate-900">{payment.household_code}</strong>
        </div>
        <div>
          <span className="text-slate-500">Người nộp tiền:</span>{' '}
          <strong className="text-slate-900">{payment.payer_name}</strong>
        </div>
        <div>
          <span className="text-slate-500">Hình thức nộp:</span>{' '}
          <strong className="text-slate-900">
            {payment.method === 'CASH' ? 'Tiền mặt' : 'Chuyển khoản'}
          </strong>
        </div>
      </div>

      {/* Itemized Allocations Table */}
      <div className="mb-6">
        <table className="w-full text-xs text-left">
          <thead className="bg-slate-100 text-slate-700 font-semibold">
            <tr>
              <th className="py-2 px-3 rounded-l-lg">STT</th>
              <th className="py-2 px-3">Khoản thu</th>
              <th className="py-2 px-3 text-right rounded-r-lg">Số tiền gạch nợ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {payment.allocations.map((alloc, idx) => (
              <tr key={alloc.id || idx}>
                <td className="py-2.5 px-3 text-slate-400">{idx + 1}</td>
                <td className="py-2.5 px-3 font-medium text-slate-800">{alloc.fee_name}</td>
                <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-900">
                  {formatVND(alloc.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary calculation */}
      <div className="border-t border-slate-200 pt-4 space-y-1.5 text-xs text-right mb-8">
        <div className="flex justify-between">
          <span className="text-slate-500">Tổng tiền gạch nợ các khoản:</span>
          <span className="font-mono font-semibold">{formatVND(payment.allocated_amount)}</span>
        </div>
        {payment.credit_amount > 0 && (
          <div className="flex justify-between text-amber-700">
            <span>Tiền nộp thừa (chuyển vào số dư có):</span>
            <span className="font-mono font-semibold">+{formatVND(payment.credit_amount)}</span>
          </div>
        )}
        <div className="flex justify-between text-sm font-bold border-t border-slate-200 pt-2 text-blue-900">
          <span>TỔNG TIỀN THU THỰC TẾ:</span>
          <span className="font-mono text-base">{formatVND(payment.amount)}</span>
        </div>
      </div>

      {/* Signatures */}
      <div className="grid grid-cols-2 text-center text-xs mt-8 pt-4">
        <div>
          <p className="font-bold text-slate-800 uppercase">Người nộp tiền</p>
          <p className="text-[11px] text-slate-400 italic mb-14">(Ký, ghi rõ họ tên)</p>
          <p className="font-medium text-slate-700">{payment.payer_name}</p>
        </div>
        <div>
          <p className="font-bold text-slate-800 uppercase">Thủ quỹ lập biên lai</p>
          <p className="text-[11px] text-slate-400 italic mb-14">(Đã ký điện tử)</p>
          <p className="font-medium text-blue-900">{payment.collected_by_name}</p>
        </div>
      </div>

      {/* Actions (Not printed) */}
      <div className="no-print mt-8 pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
        <Button onClick={handlePrint} variant="primary" icon={<Printer className="w-4 h-4" />}>
          In biên lai điện tử
        </Button>
      </div>
    </div>
  );
};
