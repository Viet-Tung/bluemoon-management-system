import React, { useEffect, useState } from 'react';
import {
  Building2,
  Users,
  CreditCard,
  AlertTriangle,
  Receipt,
  PiggyBank,
  CheckCircle,
  Clock,
  ArrowUpRight,
  TrendingUp,
} from 'lucide-react';
import { ApiClient } from '../../api';
import { TemporaryStay } from '../../types';
import { Badge } from '../../components/common/Badge';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [expiringStays, setExpiringStays] = useState<TemporaryStay[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const stays = await ApiClient.getExpiringStays();
        setExpiringStays(stays);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num) + ' đ';
  };

  return (
    <div className="space-y-8">
      {/* Welcome Hero Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-3xl p-8 text-white relative overflow-hidden shadow-xl">
        <div className="relative z-10 max-w-2xl">
          <span className="text-xs font-bold uppercase tracking-wider bg-white/10 px-3 py-1 rounded-full text-blue-200 backdrop-blur-xs">
            Trung tâm điều hành chung cư
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-3">
            Xin chào, {user?.full_name}!
          </h1>
          <p className="text-sm text-slate-300 mt-2 leading-relaxed">
            Hệ thống quản lý cư dân và thu phí Chung cư BlueMoon. Quy mô hiện tại: 1.000 căn hộ,
            ~5.000 nhân khẩu với tỷ lệ hoàn thành thu phí tháng 11 đạt 67.5%.
          </p>

          <div className="flex flex-wrap gap-3 mt-6">
            <Link
              to="/cashier"
              className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition shadow-md shadow-blue-500/20"
            >
              <CreditCard className="w-4 h-4" />
              <span>Quầy thu tiền quầy</span>
            </Link>
            <Link
              to="/billing"
              className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition backdrop-blur-xs"
            >
              <Receipt className="w-4 h-4" />
              <span>Kỳ thu phí tháng</span>
            </Link>
          </div>
        </div>
      </div>

      {/* KPI Statistic Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold">Quy mô căn hộ</span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900">1.000</p>
          <div className="flex items-center gap-1.5 text-xs text-emerald-600 mt-2 font-medium">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>98.2% đang có hộ cư trú</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold">Tổng số nhân khẩu</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900">4.850</p>
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-2">
            <span>Thường trú: 4.620 • Tạm trú: 230</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold">Thực thu Tháng 11</span>
            <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-bold text-blue-700">{formatVND(980000000)}</p>
          <div className="flex items-center gap-1.5 text-xs text-indigo-600 mt-2 font-medium">
            <span>Mục tiêu: 1.450.000.000 đ</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs hover:shadow-md transition">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold">Quỹ vận động tự nguyện</span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <PiggyBank className="w-5 h-5" />
            </div>
          </div>
          <p className="text-2xl font-bold text-amber-700">{formatVND(72500000)}</p>
          <div className="flex items-center gap-1.5 text-xs text-amber-600 mt-2 font-medium">
            <span>2 đợt vận động đang mở</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Alerts & Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Alerts for Expiring Stays (AC-09.1, D-04) */}
        <div className="lg:col-span-1 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              <h3 className="text-sm font-bold text-slate-900">Cảnh báo sắp hết hạn</h3>
            </div>
            <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded-full">
              Hạn $\le$ 15 ngày
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-4">
            Các hồ sơ Tạm trú / Tạm vắng sắp hết hạn trong vòng 15 ngày tới cần đôn đốc cư dân gia hạn
            (US-09).
          </p>

          <div className="space-y-3">
            {expiringStays.map((stay) => (
              <div
                key={stay.id}
                className="p-3.5 rounded-xl border border-amber-200/80 bg-amber-50/50 flex items-start justify-between text-xs"
              >
                <div>
                  <div className="flex items-center gap-1.5 mb-1">
                    <strong className="text-slate-900">{stay.full_name}</strong>
                    <Badge size="sm" variant={stay.type === 'TAM_TRU' ? 'info' : 'tam_vang'}>
                      {stay.type === 'TAM_TRU' ? 'Tạm trú' : 'Tạm vắng'}
                    </Badge>
                  </div>
                  <p className="text-slate-500">Căn hộ: {stay.apartment_code || '---'}</p>
                  <p className="text-slate-500">Hết hạn: {stay.end_date}</p>
                </div>
                <div className="text-right">
                  <span className="inline-block px-2 py-1 rounded-md bg-rose-100 text-rose-800 font-bold text-[11px]">
                    Còn {stay.days_left} ngày
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Financial Overview & Collections */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Tiến độ thu nợ & Chỉ tiêu kỳ này</h3>
              <p className="text-xs text-slate-500 mt-0.5">So sánh thực thu và dự thu theo danh mục khoản phí</p>
            </div>
            <Link
              to="/debts"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>Xem chi tiết công nợ</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Progress bars for fee groups */}
          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1.5">
                <span className="text-slate-700">Phí Quản lý Vận hành (7.000 đ/m²)</span>
                <span className="text-blue-700 font-bold">598.500.000 đ / 700.000.000 đ (85.5%)</span>
              </div>
              <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                <div className="bg-blue-600 h-full rounded-full transition-all" style={{ width: '85.5%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1.5">
                <span className="text-slate-700">Phí trông giữ Ô tô (1.200.000 đ/tháng)</span>
                <span className="text-indigo-700 font-bold">240.000.000 đ / 320.000.000 đ (75.0%)</span>
              </div>
              <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                <div className="bg-indigo-600 h-full rounded-full transition-all" style={{ width: '75%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1.5">
                <span className="text-slate-700">Phí gửi Xe máy (80.000 đ/tháng)</span>
                <span className="text-emerald-700 font-bold">120.000.000 đ / 140.000.000 đ (85.7%)</span>
              </div>
              <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                <div className="bg-emerald-600 h-full rounded-full transition-all" style={{ width: '85.7%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1.5">
                <span className="text-slate-700">Tiền nước sinh hoạt (Thu hộ)</span>
                <span className="text-sky-700 font-bold">65.000.000 đ / 95.000.000 đ (68.4%)</span>
              </div>
              <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                <div className="bg-sky-600 h-full rounded-full transition-all" style={{ width: '68.4%' }} />
              </div>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-slate-400" />
              <span>Dữ liệu chốt tự động lúc 02:00 sáng hàng ngày</span>
            </span>
            <span className="font-semibold text-slate-700">Hạn nộp phí tháng 11: 20/11/2026</span>
          </div>
        </div>
      </div>
    </div>
  );
};
