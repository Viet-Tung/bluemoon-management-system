import React, { useState } from 'react';
import { Modal } from '../../components/common/Modal';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';
import { ApiClient } from '../../api';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  isFirstLogin?: boolean;
}

export const ChangePasswordModal: React.FC<ChangePasswordModalProps> = ({
  isOpen,
  onClose,
  isFirstLogin = false,
}) => {
  const { success, error } = useToast();
  const { logout, refreshUser } = useAuth();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!oldPassword) {
      error(isFirstLogin ? 'Vui lòng nhập mật khẩu tạm thời đã cấp.' : 'Vui lòng nhập mật khẩu hiện tại.');
      return;
    }

    if (newPassword.length < 8) {
      error('Mật khẩu mới phải có tối thiểu 8 ký tự.');
      return;
    }

    if (!/[A-Z]/.test(newPassword) || !/[a-z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
      error('Mật khẩu mới phải chứa ít nhất 1 chữ hoa, 1 chữ thường và 1 chữ số.');
      return;
    }

    if (newPassword !== confirmPassword) {
      error('Mật khẩu xác nhận không khớp.');
      return;
    }

    setLoading(true);
    try {
      await ApiClient.changePassword(oldPassword, newPassword);
      success('Đổi mật khẩu thành công!');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      if (isFirstLogin) {
        await refreshUser();
      }
      onClose();
    } catch (err: any) {
      error(err.message || 'Không thể đổi mật khẩu.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      preventClose={isFirstLogin}
      title={isFirstLogin ? 'Bắt buộc đổi mật khẩu lần đầu' : 'Đổi mật khẩu cá nhân'}
      description={
        isFirstLogin
          ? 'Vì lý do an toàn bảo mật, tài khoản bắt buộc phải đổi mật khẩu mới trong lần đăng nhập đầu tiên.'
          : 'Cập nhật mật khẩu định kỳ để bảo vệ tài khoản của bạn.'
      }
      footer={
        <>
          {isFirstLogin ? (
            <Button variant="outline" onClick={logout} type="button">
              Đăng xuất
            </Button>
          ) : (
            <Button variant="outline" onClick={onClose} type="button">
              Hủy bỏ
            </Button>
          )}
          <Button variant="primary" onClick={handleSubmit} isLoading={loading} type="submit">
            {isFirstLogin ? 'Kích hoạt tài khoản' : 'Cập nhật mật khẩu'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label={isFirstLogin ? 'Mật khẩu tạm thời đã cấp' : 'Mật khẩu hiện tại'}
          type="password"
          placeholder={
            isFirstLogin
              ? 'Nhập mật khẩu tạm thời bạn vừa dùng để đăng nhập...'
              : 'Nhập mật khẩu cũ...'
          }
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
          required
        />
        <Input
          label="Mật khẩu mới"
          type="password"
          placeholder="Tối thiểu 8 ký tự, gồm chữ hoa, thường, số..."
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
        />
        <Input
          label="Xác nhận mật khẩu mới"
          type="password"
          placeholder="Nhập lại mật khẩu mới..."
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />

        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-1">
          <p className="font-semibold text-slate-700">Quy chuẩn mật khẩu an toàn:</p>
          <ul className="list-disc pl-4 space-y-0.5">
            <li>Độ dài tối thiểu 8 ký tự</li>
            <li>Có ít nhất 1 chữ in hoa (A-Z) và 1 chữ thường (a-z)</li>
            <li>Có ít nhất 1 chữ số (0-9)</li>
          </ul>
        </div>
      </form>
    </Modal>
  );
};
