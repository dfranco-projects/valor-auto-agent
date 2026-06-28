import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-lg border border-border bg-surface-low px-3 text-sm transition-colors",
        "placeholder:text-muted hover:border-border-strong focus-visible:outline-none",
        "focus-visible:border-primary/60 focus-visible:ring-2 focus-visible:ring-primary/25",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
