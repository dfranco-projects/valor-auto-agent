"use client";

import { useState } from "react";
import { Filters } from "@/lib/api";
import { BRAND_SLUGS, brandLabel, FUELS, TRANSMISSIONS } from "@/lib/labels";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Select } from "./ui/select";
import { Card } from "./ui/card";

const str = (v: Filters[string] | undefined, fallback = "") =>
  v == null ? fallback : String(v);

export function FilterForm({
  prefill,
  note,
  busy,
  onSubmit,
  submitLabel,
  busyLabel,
}: {
  prefill: Filters;
  note?: string;
  busy: boolean;
  onSubmit: (f: Filters) => void;
  submitLabel?: string;
  busyLabel?: string;
}) {
  const p = prefill ?? {};
  const [v, setV] = useState({
    brand: str(p.brand),
    model: str(p.model),
    year_min: str(p.year_min, "2015"),
    year_max: str(p.year_max, "2024"),
    km_max: str(p.km_max, "200000"),
    price_min: str(p.price_min, "0"),
    price_max: str(p.price_max, "20000"),
    fuel: str(p.fuel),
    transmission: str(p.transmission),
    location: str(p.location),
  });
  const set = (k: keyof typeof v, val: string) => setV((s) => ({ ...s, [k]: val }));

  const submit = () => {
    const raw: Filters = {
      brand: v.brand || null,
      model: v.model || null,
      year_min: Number(v.year_min) || null,
      year_max: Number(v.year_max) || null,
      km_max: Number(v.km_max) || null,
      price_min: Number(v.price_min) || null,
      price_max: Number(v.price_max) || null,
      fuel: v.fuel || null,
      transmission: v.transmission || null,
      location: v.location || null,
    };
    onSubmit(Object.fromEntries(Object.entries(raw).filter(([, x]) => x !== null && x !== "")));
  };

  return (
    <Card className="border-primary/30">
      <p className="mb-3 text-sm text-primary">
        {note || "Confirm or adjust the pre-filled filters, then scrape."}
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="brand">
          <Select value={v.brand} onChange={(e) => set("brand", e.target.value)}>
            {BRAND_SLUGS.map((s) => (
              <option key={s} value={s}>
                {brandLabel(s)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="model">
          <Input value={v.model} onChange={(e) => set("model", e.target.value)} />
        </Field>
        <Field label="year min">
          <Input type="number" value={v.year_min} onChange={(e) => set("year_min", e.target.value)} />
        </Field>
        <Field label="year max">
          <Input type="number" value={v.year_max} onChange={(e) => set("year_max", e.target.value)} />
        </Field>
        <Field label="price min €">
          <Input type="number" value={v.price_min} onChange={(e) => set("price_min", e.target.value)} />
        </Field>
        <Field label="price max €">
          <Input type="number" value={v.price_max} onChange={(e) => set("price_max", e.target.value)} />
        </Field>
        <Field label="km max">
          <Input type="number" value={v.km_max} onChange={(e) => set("km_max", e.target.value)} />
        </Field>
        <Field label="location">
          <Input value={v.location} onChange={(e) => set("location", e.target.value)} />
        </Field>
        <Field label="fuel">
          <Select value={v.fuel} onChange={(e) => set("fuel", e.target.value)}>
            {FUELS.map((f) => (
              <option key={f} value={f}>
                {f || "any"}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="transmission">
          <Select value={v.transmission} onChange={(e) => set("transmission", e.target.value)}>
            {TRANSMISSIONS.map((t) => (
              <option key={t} value={t}>
                {t || "any"}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <Button className="mt-4 w-full" onClick={submit} disabled={busy}>
        {busy ? (busyLabel ?? "Scraping olx + standvirtual…") : (submitLabel ?? "Scrape")}
      </Button>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {label}
      {children}
    </label>
  );
}
