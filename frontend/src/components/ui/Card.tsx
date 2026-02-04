import { cn } from "../../utils/helpers";
import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function Card({
  children,
  className,
  contentClassName,
  title,
  subtitle,
  actions,
}: CardProps) {
  return (
    <div
      className={cn(
        "bg-bg-secondary border border-border rounded-xl overflow-hidden shadow-sm",
        className,
      )}
    >
      {(title || subtitle || actions) && (
        <div className="px-6 py-4 border-b border-border flex items-center justify-between gap-4">
          <div className="min-w-0">
            {title && (
              <h3 className="text-base font-semibold text-text-primary tracking-tight">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-text-secondary mt-0.5">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}
      <div className={cn("p-6", contentClassName)}>{children}</div>
    </div>
  );
}
