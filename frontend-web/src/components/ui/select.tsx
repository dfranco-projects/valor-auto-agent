import * as React from "react";
import { cn } from "@/lib/utils";

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-10 w-full rounded-lg border border-border bg-surface-low px-2.5 text-sm transition-colors",
      "hover:border-border-strong focus-visible:outline-none focus-visible:border-primary/60",
      "focus-visible:ring-2 focus-visible:ring-primary/25",
      className,
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";
