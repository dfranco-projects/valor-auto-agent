// display labels for models and brands — slugs match olx.pt / standvirtual.pt brand paths.
export const MODEL_LABELS: Record<string, string> = {
  "claude-opus-4-8": "Claude Opus 4.8",
  "claude-sonnet-4-6": "Claude Sonnet 4.6",
  "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
  "gemini-3.5-flash": "Gemini 3.5 Flash",
  "gemini-3.1-pro": "Gemini 3.1 Pro",
  "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
  "gemini-2.5-pro": "Gemini 2.5 Pro",
  "gemini-2.5-flash": "Gemini 2.5 Flash",
};

export const modelLabel = (id: string) => MODEL_LABELS[id] ?? id;

export const CAR_BRANDS: Record<string, string> = {
  "": "Any brand",
  "alfa-romeo": "Alfa Romeo",
  audi: "Audi",
  bmw: "BMW",
  byd: "BYD",
  chevrolet: "Chevrolet",
  citroen: "Citroën",
  cupra: "Cupra",
  dacia: "Dacia",
  ds: "DS",
  fiat: "Fiat",
  ford: "Ford",
  honda: "Honda",
  hyundai: "Hyundai",
  jaguar: "Jaguar",
  jeep: "Jeep",
  kia: "Kia",
  "land-rover": "Land Rover",
  lexus: "Lexus",
  mazda: "Mazda",
  "mercedes-benz": "Mercedes-Benz",
  mg: "MG",
  mini: "MINI",
  mitsubishi: "Mitsubishi",
  nissan: "Nissan",
  opel: "Opel",
  peugeot: "Peugeot",
  porsche: "Porsche",
  renault: "Renault",
  seat: "SEAT",
  skoda: "Škoda",
  smart: "smart",
  suzuki: "Suzuki",
  tesla: "Tesla",
  toyota: "Toyota",
  volkswagen: "Volkswagen",
  volvo: "Volvo",
};

export const BRAND_SLUGS = Object.keys(CAR_BRANDS);
export const brandLabel = (slug: string) => CAR_BRANDS[slug] ?? slug;

export const FUELS = ["", "gasolina", "diesel", "hibrido", "eletrico", "gpl"];
export const TRANSMISSIONS = ["", "manual", "automatica"];

export const isGemini = (model: string) => model.startsWith("gemini");
