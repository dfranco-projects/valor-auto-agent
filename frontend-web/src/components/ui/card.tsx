import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface p-4 shadow-[0_1px_2px_rgba(20,30,50,0.05)]",
        className,
      )}
      {...props}
    />
  );
}
