import React, { useEffect, useState } from 'react';
import {
  PiggyBank,
  Plus,
  HeartHandshake,
  Receipt,
  FileDown,
  Printer,
  ShieldCheck,
  CheckCircle,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { Donation, DonationCampaign } from '../../types';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';

export const DonationCampaignsPage: React.FC = () => {
  const { success, error } = useToast();
  const { hasRole } = useAuth();
  const [campaigns, setCampaigns] = useState<DonationCampaign[]>([]);
  const [donations, setDonations] = useState<Donation[]>([]);

  // Modal Donate (US-41)
  const [donateModalOpen, setDonateModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<DonationCampaign | null>(null);
  const [donorName, setDonorName] = useState('Phạm Minh Tuấn (Căn B1204)');
  const [amount, setAmount] = useState(500000);
  const [method, setMethod] = useState<'CASH' | 'BANK_TRANSFER'>('CASH');

  // Modal Voucher Print
  const [lastVoucher, setLastVoucher] = useState<Donation | null>(null);

  // Settlement Report Modal (US-42)
  const [settlementModalOpen, setSettlementModalOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const camp = await ApiClient.getDonationCampaigns();
      setCampaigns(camp);
    } catch (err: any) {
      error(err.message);
    }
  };

  const handleDonate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCampaign) return;
    if (amount <= 0) {
      error('Số tiền ủng hộ phải lớn hơn 0.');
      return;
    }

    try {
      const d = await ApiClient.addDonation({
        campaign_id: selectedCampaign.id,
        household_id: 1,
        donor_name: donorName,
        amount,
        method,
      });

      success(`Ghi nhận đóng góp thành công! Đã tạo phiếu thu số #${d.voucher_no} (US-41).`);
      setDonateModalOpen(false);
      setLastVoucher(d);
      loadData();
    } catch (err: any) {
      error(err.message);
    }
  };

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  const isResident = hasRole('RESIDENT');

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <PiggyBank className="w-6 h-6 text-amber-600" />
            <span>Quỹ Vận Động Tự Nguyện (US-40, US-41, US-42)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Quản lý các đợt vận động tự nguyện (Vì người nghèo, Khuyến học...). Tách biệt hoàn toàn khỏi công nợ bắt buộc và bảo mật số tiền đóng góp từng hộ (AC-40.1, WL-026).
          </p>
        </div>

        {!isResident && (
          <Button
            onClick={() => setSettlementModalOpen(true)}
            variant="outline"
            icon={<FileDown className="w-4 h-4" />}
          >
            Báo cáo quyết toán mẫu Phường (US-42)
          </Button>
        )}
      </div>

      {/* Campaigns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {campaigns.map((camp) => (
          <div
            key={camp.id}
            className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs hover:shadow-md transition space-y-5"
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-mono text-slate-400 font-bold uppercase tracking-wider">
                  Mã đợt: {camp.code}
                </span>
                <h3 className="text-base font-bold text-slate-900 mt-1">{camp.name}</h3>
                <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">{camp.description}</p>
              </div>
              <Badge variant={camp.status === 'ACTIVE' ? 'success' : 'neutral'} dot>
                {camp.status === 'ACTIVE' ? 'Đang vận động' : 'Đã kết thúc'}
              </Badge>
            </div>

            <div className="bg-amber-50/60 p-4 rounded-2xl border border-amber-100 flex items-center justify-between text-xs">
              <div>
                <p className="text-slate-500 text-[11px]">Tổng số tiền quyên góp</p>
                <p className="text-xl font-bold font-mono text-amber-800 mt-0.5">
                  {formatVND(camp.total_raised)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-slate-500 text-[11px]">Số hộ tham gia</p>
                <p className="text-base font-bold text-slate-800 mt-0.5">{camp.total_donors} hộ dân</p>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                Thời gian: {camp.start_date} đến {camp.end_date || 'Không thời hạn'}
              </span>

              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  setSelectedCampaign(camp);
                  setDonateModalOpen(true);
                }}
                icon={<HeartHandshake className="w-4 h-4" />}
              >
                Ghi nhận đóng góp
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal Donate (US-41) */}
      {selectedCampaign && (
        <Modal
          isOpen={donateModalOpen}
          onClose={() => setDonateModalOpen(false)}
          title={`Ghi nhận ủng hộ: ${selectedCampaign.name}`}
          description="Khoản đóng góp tự nguyện tùy tâm của cư dân, tuyệt đối không tính vào công nợ bắt buộc (AC-40.1)."
        >
          <form onSubmit={handleDonate} className="space-y-4">
            <Input
              label="Họ tên người ủng hộ / Căn hộ"
              value={donorName}
              onChange={(e) => setDonorName(e.target.value)}
              required
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Số tiền ủng hộ (VNĐ - tùy tâm)
              </label>
              <input
                type="number"
                step="10000"
                min="10000"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-base font-mono font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Phương thức đóng góp
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setMethod('CASH')}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold border ${
                    method === 'CASH'
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-slate-700 border-slate-300'
                  }`}
                >
                  Tiền mặt tại quầy
                </button>
                <button
                  type="button"
                  onClick={() => setMethod('BANK_TRANSFER')}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold border ${
                    method === 'BANK_TRANSFER'
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-slate-700 border-slate-300'
                  }`}
                >
                  Chuyển khoản tài khoản quỹ
                </button>
              </div>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-600 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <span>
                Quy tắc bảo mật (WL-026): Số tiền ủng hộ chi tiết của từng hộ được giữ riêng tư, các cư dân khác chỉ xem được tổng số tiền chung của cả đợt vận động.
              </span>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button variant="outline" type="button" onClick={() => setDonateModalOpen(false)}>
                Hủy
              </Button>
              <Button variant="primary" type="submit">
                Xác nhận & Xuất phiếu thu (QT)
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal Printable Voucher QT00000001 (US-41) */}
      {lastVoucher && (
        <Modal
          isOpen={!!lastVoucher}
          onClose={() => setLastVoucher(null)}
          title={`Phiếu Xác Nhận Đóng Góp Quỹ #${lastVoucher.voucher_no}`}
        >
          <div className="bg-amber-50/40 border border-amber-200 rounded-2xl p-6 text-xs space-y-4 printable-area">
            <div className="text-center border-b border-amber-200 pb-3">
              <p className="font-bold text-amber-900 text-sm uppercase">PHIẾU XÁC NHẬN ĐÓNG GÓP TỰ NGUYỆN</p>
              <p className="font-mono text-xs text-amber-700 font-bold mt-1">Số: {lastVoucher.voucher_no}</p>
            </div>

            <div className="space-y-1.5">
              <p>Đợt vận động: <strong className="text-slate-900">{lastVoucher.campaign_name}</strong></p>
              <p>Người ủng hộ: <strong className="text-slate-900">{lastVoucher.donor_name}</strong></p>
              <p>Số tiền ủng hộ: <strong className="text-base text-amber-900 font-mono">{formatVND(lastVoucher.amount)}</strong></p>
              <p>Hình thức: <span className="font-semibold">{lastVoucher.method === 'CASH' ? 'Tiền mặt' : 'Chuyển khoản'}</span></p>
              <p>Thời gian: {new Date(lastVoucher.donated_at).toLocaleString('vi-VN')}</p>
            </div>

            <p className="text-center italic text-slate-500 pt-3 border-t border-amber-200">
              Ban Quản Trị Chung cư BlueMoon trân trọng cảm ơn tấm lòng hảo tâm của quý cư dân!
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4 mt-4 border-t border-slate-100 no-print">
            <Button variant="primary" icon={<Printer className="w-4 h-4" />} onClick={() => window.print()}>
              In phiếu xác nhận
            </Button>
          </div>
        </Modal>
      )}

      {/* Modal Settlement Report (US-42) */}
      <Modal
        isOpen={settlementModalOpen}
        onClose={() => setSettlementModalOpen(false)}
        title="Báo cáo Quyết toán Quỹ Vận động theo Biểu mẫu Phường (US-42)"
        size="lg"
      >
        <div className="space-y-4 text-xs printable-area">
          <div className="text-center space-y-1 border-b border-slate-200 pb-4">
            <p className="font-bold uppercase tracking-wider text-slate-800">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</p>
            <p className="text-[11px] text-slate-500">Độc lập - Tự do - Hạnh phúc</p>
            <h3 className="text-base font-bold text-slate-900 mt-2 uppercase">
              BẢNG TỔNG HỢP QUYẾT TOÁN QUỸ VẬN ĐỘNG NĂM 2026
            </h3>
            <p className="text-slate-500 italic">Kính gửi: Ủy ban Mặt trận Tổ quốc Phường & UBND Phường</p>
          </div>

          <table className="w-full text-xs text-left border border-slate-200">
            <thead className="bg-slate-100 text-slate-800 font-bold">
              <tr>
                <th className="p-2 border border-slate-200">STT</th>
                <th className="p-2 border border-slate-200">Tên đợt vận động</th>
                <th className="p-2 border border-slate-200 text-center">Số hộ ủng hộ</th>
                <th className="p-2 border border-slate-200 text-right">Tổng số tiền thu (VNĐ)</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c, idx) => (
                <tr key={c.id}>
                  <td className="p-2 border border-slate-200 text-center">{idx + 1}</td>
                  <td className="p-2 border border-slate-200 font-medium">{c.name}</td>
                  <td className="p-2 border border-slate-200 text-center">{c.total_donors} hộ</td>
                  <td className="p-2 border border-slate-200 text-right font-mono font-bold">
                    {formatVND(c.total_raised)}
                  </td>
                </tr>
              ))}
              <tr className="bg-slate-50 font-bold">
                <td colSpan={3} className="p-2 border border-slate-200 text-right uppercase">
                  Tổng cộng tiền quyết toán bàn giao:
                </td>
                <td className="p-2 border border-slate-200 text-right font-mono text-sm text-blue-900">
                  {formatVND(campaigns.reduce((sum, c) => sum + c.total_raised, 0))}
                </td>
              </tr>
            </tbody>
          </table>

          <div className="grid grid-cols-2 text-center pt-8">
            <div>
              <p className="font-bold">Đại diện Kế toán BQT</p>
              <p className="text-[11px] text-slate-400 mb-10">(Ký, họ tên)</p>
              <p className="font-medium">Trần Thị Thu Trang</p>
            </div>
            <div>
              <p className="font-bold">Trưởng Ban Quản Trị Tòa Nhà</p>
              <p className="text-[11px] text-slate-400 mb-10">(Ký, đóng dấu)</p>
              <p className="font-medium text-blue-900">Nguyễn Văn Quản Trị</p>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 no-print">
            <Button variant="primary" icon={<Printer className="w-4 h-4" />} onClick={() => window.print()}>
              In biên bản quyết toán
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
