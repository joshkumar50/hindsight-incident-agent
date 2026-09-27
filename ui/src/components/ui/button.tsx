import React from 'react';
import { clsx } from 'clsx';

type ButtonVariant = 'default' | 'outline' | 'ghost' | 'destructive' | 'secondary';
type ButtonSize = 'sm' | 'default' | 'lg' | 'icon';

const variantStyles: Record<ButtonVariant, string> = {
  default:     'bg-slate-900 text-white hover:bg-slate-800',
  outline:     'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300',
  ghost:       'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  destructive: 'bg-red-600 text-white hover:bg-red-700',
  secondary:   'bg-slate-100 text-slate-700 hover:bg-slate-200',
};
const sizeStyles: Record<ButtonSize, string> = {
  sm:      'h-7 px-3 text-xs',
  default: 'h-9 px-4 text-sm',
  lg:      'h-11 px-6 text-sm',
  icon:    'h-9 w-9',
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={clsx(
        'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:pointer-events-none',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = 'Button';
