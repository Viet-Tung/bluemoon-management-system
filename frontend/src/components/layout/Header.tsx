import React, { useState, useEffect, useRef } from 'react';
import {
  Menu,
  LogOut,
  KeyRound,
  ChevronDown,
  Search,
  X,
  Building2,
  Home,
  User as UserIcon,
  Car,
  Loader2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ApiClient } from '../../api';
import { SearchHit, SearchEntityType } from '../../types';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';

interface HeaderProps {
  onToggleSidebar: () => void;
  onChangePassword: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, onChangePassword }) => {
  const { user, role, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Omnibox global search state (US-23: ADMIN, ACCOUNTANT, TREASURER)
  const canSearch = hasRole('ADMIN', 'ACCOUNTANT', 'TREASURER');
  const canNavigateModules = hasRole('ADMIN', 'ACCOUNTANT');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchHits, setSearchHits] = useState<SearchHit[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [previewHit, setPreviewHit] = useState<SearchHit | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(e.target as Node)
      ) {
        setSearchOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  useEffect(() => {
    if (!canSearch) return;
    const q = searchQuery.trim();
    if (!q) {
      setSearchHits([]);
      setSearchError(null);
      setSearching(false);
      return;
    }

    let cancelled = false;
    setSearching(true);
    setSearchError(null);

    const timer = setTimeout(async () => {
      try {
        const res = await ApiClient.globalSearch(q, 10);
        if (!cancelled) {
          setSearchHits(res.items || []);
          setSearchOpen(true);
        }
      } catch (err: any) {
        if (!cancelled) {
          setSearchError(err.message || 'Không thể tìm kiếm lúc này.');
          setSearchHits([]);
        }
      } finally {
        if (!cancelled) {
          setSearching(false);
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [searchQuery, canSearch]);

  const getRoleDisplayName = (code?: string) => {
    switch (code) {
      case 'ADMIN':
        return 'Ban Quản Trị';
      case 'ACCOUNTANT':
        return 'Kế toán viên';
      case 'TREASURER':
        return 'Thủ quỹ';
      case 'RESIDENT':
        return 'Cư dân';
      default:
        return code || 'Người dùng';
    }
  };

  const getEntityMeta = (type: SearchEntityType) => {
    switch (type) {
      case 'APARTMENT':
        return { label: 'Căn hộ', variant: 'info' as const, Icon: Building2 };
      case 'HOUSEHOLD':
        return { label: 'Hộ gia đình', variant: 'purple' as const, Icon: Home };
      case 'RESIDENT':
        return { label: 'Nhân khẩu', variant: 'success' as const, Icon: UserIcon };
      case 'VEHICLE':
        return { label: 'Phương tiện', variant: 'warning' as const, Icon: Car };
      default:
        return { label: type, variant: 'neutral' as const, Icon: Search };
    }
  };

  const TITLE_PREFIX_BY_ENTITY: Partial<Record<SearchEntityType, string>> = {
    APARTMENT: 'Căn hộ ',
    HOUSEHOLD: 'Hộ ',
    VEHICLE: 'Biển số ',
  };

  const extractSearchKeyword = (hit: SearchHit): string => {
    const prefix = TITLE_PREFIX_BY_ENTITY[hit.entity_type];
    if (prefix && hit.title.startsWith(prefix)) {
      return hit.title.slice(prefix.length).trim();
    }
    return hit.title.trim();
  };

  const handleSelectHit = (hit: SearchHit) => {
    setSearchOpen(false);
    if (!canNavigateModules) {
      // TREASURER chỉ xem kết quả tra cứu nhanh, tránh điều hướng vào màn hình không có quyền
      setPreviewHit(hit);
      return;
    }

    const keyword = extractSearchKeyword(hit);
    switch (hit.entity_type) {
      case 'APARTMENT':
        navigate(`/apartments?tab=apartments&q=${encodeURIComponent(keyword)}`);
        break;
      case 'HOUSEHOLD':
        navigate(`/apartments?tab=households&q=${encodeURIComponent(keyword)}`);
        break;
      case 'RESIDENT':
        if (hit.household_id) {
          navigate(`/residents?household_id=${hit.household_id}`);
        } else {
          navigate('/residents');
        }
        break;
      case 'VEHICLE':
        navigate(`/vehicles?q=${encodeURIComponent(keyword)}`);
        break;
      default:
        setPreviewHit(hit);
    }
  };

  return (
    <>
      <header className="no-print sticky top-0 z-30 h-16 bg-white/90 backdrop-blur-md border-b border-slate-200 px-6 flex items-center justify-between gap-4">
        {/* Left side */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={onToggleSidebar}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition"
            title="Thu gọn / Mở rộng thanh điều hướng"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="hidden md:inline-block text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-lg">
            Chung cư BlueMoon
          </span>
        </div>

        {/* Center: Global Omnibox Search (US-23) */}
        {canSearch && (
          <div ref={searchContainerRef} className="relative flex-1 max-w-md">
            <div className="relative flex items-center">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onFocus={() => {
                  if (searchQuery.trim()) setSearchOpen(true);
                }}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSearchOpen(true);
                }}
                placeholder="Tìm nhanh căn hộ, hộ gia đình, cư dân, biển số xe..."
                className="w-full bg-slate-100/80 hover:bg-slate-100 focus:bg-white border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 rounded-xl pl-9 pr-9 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 transition outline-none"
              />
              {searching ? (
                <Loader2 className="w-3.5 h-3.5 text-blue-600 animate-spin absolute right-3" />
              ) : (
                searchQuery && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery('');
                      setSearchHits([]);
                      setSearchOpen(false);
                    }}
                    className="p-0.5 text-slate-400 hover:text-slate-600 absolute right-2.5 rounded"
                    title="Xóa tìm kiếm"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )
              )}
            </div>

            {searchOpen && searchQuery.trim() && (
              <div className="absolute left-0 right-0 mt-2 bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden z-50 max-h-96 overflow-y-auto">
                <div className="px-3.5 py-2 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Kết quả tìm kiếm nhanh</span>
                  {!searching && <span>{searchHits.length} kết quả</span>}
                </div>

                {searchError ? (
                  <div className="p-4 text-xs text-rose-600">{searchError}</div>
                ) : searching && searchHits.length === 0 ? (
                  <div className="p-4 text-xs text-slate-400 text-center">Đang tìm kiếm...</div>
                ) : searchHits.length === 0 ? (
                  <div className="p-4 text-xs text-slate-400 text-center">
                    Không tìm thấy kết quả phù hợp cho "{searchQuery.trim()}".
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {searchHits.map((hit) => {
                      const meta = getEntityMeta(hit.entity_type);
                      const Icon = meta.Icon;
                      return (
                        <button
                          key={`${hit.entity_type}-${hit.entity_id}`}
                          type="button"
                          onClick={() => handleSelectHit(hit)}
                          className="w-full px-3.5 py-2.5 hover:bg-blue-50/60 transition flex items-center justify-between gap-3 text-left"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center flex-shrink-0">
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-slate-900 truncate">
                                {hit.title}
                              </p>
                              {hit.subtitle && (
                                <p className="text-[11px] text-slate-500 truncate mt-0.5">
                                  {hit.subtitle}
                                </p>
                              )}
                            </div>
                          </div>
                          <Badge variant={meta.variant} size="sm" className="flex-shrink-0">
                            {meta.label}
                          </Badge>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Right side: Authenticated User Profile */}
        <div className="flex items-center gap-4 flex-shrink-0">
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 p-1.5 hover:bg-slate-100 rounded-xl transition text-left"
            >
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white font-bold text-xs shadow-xs">
                {user?.full_name?.charAt(0) || 'U'}
              </div>
              <div className="hidden sm:block text-xs">
                <p className="font-semibold text-slate-800 leading-tight truncate max-w-[160px]">
                  {user?.full_name || user?.username}
                </p>
                <div className="mt-0.5">
                  <Badge size="sm" variant="info">
                    {user?.role?.name || getRoleDisplayName(role || undefined)}
                  </Badge>
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {/* Dropdown popup */}
            {dropdownOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div className="px-4 py-3 border-b border-slate-100">
                    <p className="text-xs text-slate-500">Tài khoản đăng nhập</p>
                    <p className="text-sm font-bold text-slate-800">{user?.username}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {user?.email || 'Chưa cập nhật email'}
                    </p>
                  </div>

                  <div className="p-2 space-y-1">
                    <button
                      onClick={() => {
                        setDropdownOpen(false);
                        onChangePassword();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:text-blue-600 hover:bg-blue-50/50 rounded-xl transition text-left"
                    >
                      <KeyRound className="w-4 h-4 text-slate-400" />
                      <span>Đổi mật khẩu tài khoản</span>
                    </button>

                    <button
                      onClick={async () => {
                        setDropdownOpen(false);
                        await logout();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 rounded-xl transition text-left"
                    >
                      <LogOut className="w-4 h-4 text-rose-500" />
                      <span>Đăng xuất hệ thống</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Preview Modal for roles without module navigation (e.g. TREASURER) */}
      {previewHit && (
        <Modal
          isOpen={true}
          onClose={() => setPreviewHit(null)}
          title="Thông tin tra cứu nhanh"
          description="Chi tiết bản ghi từ công cụ tìm kiếm toàn hệ thống."
        >
          <div className="space-y-3 text-xs">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Loại dữ liệu</span>
                <Badge variant={getEntityMeta(previewHit.entity_type).variant} size="sm">
                  {getEntityMeta(previewHit.entity_type).label}
                </Badge>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-slate-500">Tiêu đề</span>
                <span className="font-bold text-slate-900 text-right">{previewHit.title}</span>
              </div>
              {previewHit.subtitle && (
                <div className="flex items-start justify-between gap-4">
                  <span className="text-slate-500 flex-shrink-0">Thông tin thêm</span>
                  <span className="text-slate-700 text-right">{previewHit.subtitle}</span>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Mã định danh</span>
                <span className="font-mono text-slate-700">#{previewHit.entity_id}</span>
              </div>
              {previewHit.household_id && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Mã hộ gia đình</span>
                  <span className="font-mono text-slate-700">#{previewHit.household_id}</span>
                </div>
              )}
            </div>
            <div className="flex justify-end">
              <Button variant="primary" size="sm" onClick={() => setPreviewHit(null)}>
                Đóng
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};
