import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Lock, User, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { useToast } from '../../context/ToastContext';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const { error: toastError } = useToast();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLocked, setIsLocked] = useState(false);

  // If already authenticated and not loading, redirect to dashboard
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLocked(false);

    if (!username.trim() || !password) {
      setErrorMessage('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.');
      return;
    }

    setSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      const msg = err.message || 'Đăng nhập không thành công. Vui lòng thử lại.';
      setErrorMessage(msg);
      toastError(msg);

      if (err.code === 'ACCOUNT_LOCKED') {
        setIsLocked(true);
      }
    } finally {
      setSubmitting(false);
    }
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

        {/* Error / Account Locked Banner */}
        {errorMessage && (
          <div
            className={`mb-6 p-4 rounded-2xl text-xs flex items-start gap-3 border ${
              isLocked
                ? 'bg-rose-50 border-rose-200 text-rose-800'
                : 'bg-amber-50 border-amber-200 text-amber-900'
            }`}
          >
            <AlertCircle
              className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                isLocked ? 'text-rose-600' : 'text-amber-600'
              }`}
            />
            <div>
              <p className="font-bold">
                {isLocked ? 'Tài khoản đã bị tạm khóa' : 'Đăng nhập không thành công'}
              </p>
              <p className="mt-0.5 leading-relaxed">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <Input
            label="Tên đăng nhập"
            placeholder="Nhập tên đăng nhập hệ thống..."
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              if (errorMessage) setErrorMessage(null);
            }}
            icon={<User className="w-4 h-4" />}
            required
            autoComplete="username"
          />

          <Input
            label="Mật khẩu"
            type="password"
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (errorMessage) setErrorMessage(null);
            }}
            icon={<Lock className="w-4 h-4" />}
            required
            autoComplete="current-password"
          />

          <Button
            type="submit"
            variant="primary"
            className="w-full mt-2"
            size="lg"
            isLoading={submitting}
            icon={<ArrowRight className="w-4 h-4" />}
          >
            Đăng nhập hệ thống
          </Button>
        </form>
      </div>
    </div>
  );
};
