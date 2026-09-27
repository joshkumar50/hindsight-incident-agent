import React from 'react';
import { clsx } from 'clsx';

type BadgeVariant = 'default' | 'outline' | 'secondary' | 'destructive' | 'success' | 'warning' | 'investigating' | 'resolved';

const variantStyles: Record<BadgeVariant, string> = {
  default:       'bg-slate-900 text-white',
  outline:       'border border-slate-300 text-slate-700 bg-transparent',
  secondary:     'bg-slate-100 text-slate-700',
  destructive:   'bg-red-100 text-red-700',
  success:       'bg-emerald-50 text-emerald-700 border border-emerald-200',
  warning:       'bg-amber-50 text-amber-700 border border-amber-200',
  investigating: 'bg-amber-50 text-amber-700 border border-amber-200',
  resolved:      'bg-emerald-50 text-emerald-700 border border-emerald-200',
};

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export const Badge = ({ className, variant = 'default', ...props }: BadgeProps) => (
  <span
    className={clsx(
      'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
      variantStyles[variant],
      className
    )}
    {...props}
  />
);
