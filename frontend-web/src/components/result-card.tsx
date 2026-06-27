import { SearchResult } from "@/lib/api";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";

export function ResultCard({ rank, r }: { rank: number; r: SearchResult }) {
  const price = r.price_eur ? `${r.price_eur.toLocaleString("pt-PT")} €` : "n/a";
  return (
    <Card className="flex gap-3">
      <div className="w-7 shrink-0 font-mono text-lg text-primary">{rank}</div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="rounded bg-primary-container px-1.5 py-0.5 text-xs font-semibold text-on-primary-container">
            {r.score.toFixed(1)}
          </span>
          <a
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="truncate font-medium hover:text-primary"
          >
            {r.title ?? "(untitled)"}
          </a>
        </div>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          <Badge>{price}</Badge>
          {r.year != null && <Badge>{r.year}</Badge>}
          {r.km != null && <Badge>{r.km.toLocaleString("pt-PT")} km</Badge>}
          <Badge>{r.source}</Badge>
        </div>
        {r.rationale && <p className="mt-2 text-sm text-muted">{r.rationale}</p>}
      </div>
    </Card>
  );
}
