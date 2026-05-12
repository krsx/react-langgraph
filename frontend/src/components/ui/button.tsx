import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline" | "danger";
};

const variants = {
  primary:
    "bg-primary text-primary-foreground shadow-sm hover:opacity-90",
  ghost:
    "bg-transparent text-foreground hover:bg-secondary",
  outline:
    "border border-border bg-card text-foreground hover:bg-secondary",
  danger:
    "bg-destructive text-destructive-foreground hover:opacity-90",
};

export function Button({
  className,
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
