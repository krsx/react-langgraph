import type { SelectHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
};

export function SelectField({ className, label, children, ...props }: SelectProps) {
  return (
    <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
      <span>{label}</span>
      <select
        className={cn(
          "rounded-xl border border-border bg-card px-3 py-2 text-sm text-foreground shadow-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/25",
          className,
        )}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}
