import * as React from "react";
import { cn } from "@/lib/utils";

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-9 w-full rounded-md border border-border bg-surface-low px-2 text-sm",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60",
      className,
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";
