import React from 'react';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'purple'
  | 'paid'
  | 'partial'
  | 'unpaid'
  | 'thuong_tru'
  | 'tam_vang';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  className = '',
}) => {
  const sizes = {
    sm: 'text-[11px] px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-semibold',
  };

  const variants: Record<BadgeVariant, { bg: string; dotColor: string }> = {
    success: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', dotColor: 'bg-emerald-500' },
    warning: { bg: 'bg-amber-50 text-amber-700 border-amber-200', dotColor: 'bg-amber-500' },
    danger: { bg: 'bg-rose-50 text-rose-700 border-rose-200', dotColor: 'bg-rose-500' },
    info: { bg: 'bg-sky-50 text-sky-700 border-sky-200', dotColor: 'bg-sky-500' },
    neutral: { bg: 'bg-slate-100 text-slate-700 border-slate-200', dotColor: 'bg-slate-400' },
    purple: { bg: 'bg-purple-50 text-purple-700 border-purple-200', dotColor: 'bg-purple-500' },

    // BlueMoon Domain specific
    paid: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', dotColor: 'bg-emerald-500' },
    partial: { bg: 'bg-amber-50 text-amber-700 border-amber-200', dotColor: 'bg-amber-500' },
    unpaid: { bg: 'bg-rose-50 text-rose-700 border-rose-200', dotColor: 'bg-rose-500' },
    thuong_tru: { bg: 'bg-blue-50 text-blue-700 border-blue-200', dotColor: 'bg-blue-500' },
    tam_vang: { bg: 'bg-purple-50 text-purple-700 border-purple-200', dotColor: 'bg-purple-500' },
  };

  const conf = variants[variant] || variants.neutral;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${sizes[size]} ${conf.bg} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${conf.dotColor}`} />}
      {children}
    </span>
  );
};
