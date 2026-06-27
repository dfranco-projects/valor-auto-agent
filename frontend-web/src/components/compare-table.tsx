import { SearchResult } from "@/lib/api";
import { Card } from "./ui/card";
import { Button } from "./ui/button";

const ROWS: [string, (r: SearchResult) => string][] = [
  ["score", (r) => r.score.toFixed(1)],
  ["price", (r) => (r.price_eur ? `${r.price_eur.toLocaleString("pt-PT")} €` : "—")],
  ["year", (r) => r.year?.toString() ?? "—"],
  ["km", (r) => (r.km != null ? `${r.km.toLocaleString("pt-PT")} km` : "—")],
  ["source", (r) => r.source],
  ["rationale", (r) => r.rationale || "—"],
];

export function CompareTable({ items, onClear }: { items: SearchResult[]; onClear: () => void }) {
  return (
    <Card className="border-primary/30">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          Compare ({items.length})
        </h2>
        <Button size="sm" variant="ghost" onClick={onClear}>
          Clear
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="p-2" />
              {items.map((r, i) => (
                <th key={i} className="max-w-[12rem] truncate p-2 text-left font-medium">
                  <a href={r.url} target="_blank" rel="noreferrer" className="hover:text-primary">
                    {r.title ?? "(untitled)"}
                  </a>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map(([label, get]) => (
              <tr key={label} className="border-t border-border align-top">
                <td className="p-2 text-xs uppercase tracking-wide text-muted">{label}</td>
                {items.map((r, i) => (
                  <td key={i} className="p-2">
                    {get(r)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
