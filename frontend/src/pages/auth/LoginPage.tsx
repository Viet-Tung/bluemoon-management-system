import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Lock, User, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { useToast } from '../../context/ToastContext';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { error } = useToast();

  const [username, setUsername] = useState('admin_bqt');
  const [password, setPassword] = useState('BlueMoon@2026');
  const [loading, setLoading] = useState(false);
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [lockedUntil, setLockedUntil] = useState<number | null>(null);

  // If already logged in, redirect
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (lockedUntil && Date.now() < lockedUntil) {
      const remainingSeconds = Math.ceil((lockedUntil - Date.now()) / 1000);
      error(`Tài khoản đang bị tạm khóa 15 phút do nhập sai nhiều lần. Vui lòng chờ ${remainingSeconds} giây (AC-28.2).`);
      return;
    }

    setLoading(true);
    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err: any) {
      const nextFail = failedAttempts + 1;
      setFailedAttempts(nextFail);

      if (nextFail >= 5) {
        const lockoutTime = Date.now() + 15 * 60 * 1000;
        setLockedUntil(lockoutTime);
        error('Tài khoản đã bị tạm khóa 15 phút do nhập sai 5 lần liên tiếp (AC-28.2)!');
      } else {
        error(err.message || `Đăng nhập thất bại. Bạn còn ${5 - nextFail} lần thử.`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (u: string, p: string = 'BlueMoon@2026') => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4 sm:p-6 relative overflow-hidden">
      {/* Background Decorative Rings */}
      <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-blue-600/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-indigo-600/10 blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-100 p-8 relative z-10">
        {/* Logo and Brand */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 mx-auto flex items-center justify-center text-white shadow-lg shadow-blue-500/30 mb-4">
            <Building2 className="w-8 h-8" />
          </div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Chung Cư BlueMoon</h1>
          <p className="text-xs text-slate-500 mt-1">Hệ thống Quản lý Cư dân & Thu phí Toà nhà</p>
        </div>

        {/* Account Locked Notice */}
        {lockedUntil && Date.now() < lockedUntil && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Tài khoản bị tạm khóa 15 phút</p>
              <p className="mt-0.5 leading-relaxed">
                Hệ thống kích hoạt chính sách an toàn (AC-28.2): Đăng nhập sai 5 lần liên tiếp.
              </p>
            </div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <Input
            label="Tên đăng nhập"
            placeholder="Ví dụ: admin_bqt..."
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            icon={<User className="w-4 h-4" />}
            required
          />

          <Input
            label="Mật khẩu"
            type="password"
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            icon={<Lock className="w-4 h-4" />}
            required
          />

          <Button
            type="submit"
            variant="primary"
            className="w-full mt-2"
            size="lg"
            isLoading={loading}
            icon={<ArrowRight className="w-4 h-4" />}
          >
            Đăng nhập hệ thống
          </Button>
        </form>

        {/* Quick Testing Role Fillers */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>Tài khoản thử nghiệm nhanh:</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => handleQuickFill('admin_bqt')}
              className="p-2.5 rounded-xl border border-slate-200 text-left hover:border-blue-500 hover:bg-blue-50/50 transition group"
            >
              <p className="font-bold text-slate-800 group-hover:text-blue-700">Trưởng BQT</p>
              <p className="text-[11px] text-slate-400 font-mono">admin_bqt</p>
            </button>

            <button
              type="button"
              onClick={() => handleQuickFill('ketoan_01')}
              className="p-2.5 rounded-xl border border-slate-200 text-left hover:border-blue-500 hover:bg-blue-50/50 transition group"
            >
              <p className="font-bold text-slate-800 group-hover:text-blue-700">Kế toán viên</p>
              <p className="text-[11px] text-slate-400 font-mono">ketoan_01</p>
            </button>

            <button
              type="button"
              onClick={() => handleQuickFill('thuquy_01')}
              className="p-2.5 rounded-xl border border-slate-200 text-left hover:border-blue-500 hover:bg-blue-50/50 transition group"
            >
              <p className="font-bold text-slate-800 group-hover:text-blue-700">Thủ quỹ</p>
              <p className="text-[11px] text-slate-400 font-mono">thuquy_01</p>
            </button>

            <button
              type="button"
              onClick={() => handleQuickFill('cudan_b1204')}
              className="p-2.5 rounded-xl border border-slate-200 text-left hover:border-blue-500 hover:bg-blue-50/50 transition group"
            >
              <p className="font-bold text-slate-800 group-hover:text-blue-700">Cư dân B1204</p>
              <p className="text-[11px] text-slate-400 font-mono">cudan_b1204</p>
            </button>
          </div>
          <p className="text-[11px] text-slate-400 text-center mt-3">
            Mật khẩu mặc định: <code className="font-bold text-slate-600">BlueMoon@2026</code>
          </p>
        </div>
      </div>
    </div>
  );
};
