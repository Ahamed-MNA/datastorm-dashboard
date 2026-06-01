export const fmtInt = (n: number) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n ?? 0);

export const fmtNum = (n: number, digits = 1) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(n ?? 0);

export const fmtCompact = (n: number) =>
  new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(n ?? 0);

export const fmtMoney = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "LKR", maximumFractionDigits: 0 }).format(
    n ?? 0,
  );

export const fmtMoneyCompact = (n: number) =>
  "Rs " + new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(n ?? 0);

export const fmtPct = (n: number, digits = 1) =>
  `${(n * 100).toFixed(digits)}%`;

export const fmtPctRaw = (n: number, digits = 1) =>
  `${n.toFixed(digits)}%`;

// Plain-English explanations of every model metric.
export const GLOSSARY: Record<string, string> = {
  "Historical Sales":
    "Total volume the outlet has actually sold (in liters) over the measurement period.",
  "Predicted Potential":
    "Volume this outlet COULD sell if it were operating at full efficiency, based on its size, location and surroundings.",
  "Opportunity Gap":
    "The difference between potential and actual sales — the additional liters left on the table.",
  "Growth %":
    "How much sales could grow (in %) if the outlet reached its full potential.",
  "Efficiency Score":
    "A 0–1 score for how well this outlet converts its potential into real sales. Higher is better.",
  "Inefficiency %":
    "Percent of potential currently being missed. Lower is better.",
  "ROI":
    "Return on investment for promotional spend — extra liters lifted per rupee invested.",
  "Allocated Budget":
    "Promotional rupees the optimizer recommends spending on this outlet.",
  "Expected Lift":
    "Extra sales volume expected from the recommended spend.",
  "Competitive Friction":
    "How crowded the outlet's neighborhood is with rival stores. Higher = harder competition.",
  "POI Impact":
    "Combined pull from nearby points of interest (schools, transit, religious sites etc.).",
  "Market Saturation":
    "Number of competing outlets within a 5 km radius.",
  "CV Volume":
    "How volatile this outlet's monthly sales are. High values mean inconsistent buying patterns.",
  "Cooler Count":
    "Number of refrigeration units installed — a key driver of beverage sales.",
  "b_param":
    "Solver elasticity. Higher values spread the budget more evenly across outlets; lower values concentrate it on the best opportunities.",
};

export const glossary = (key: string) => GLOSSARY[key] ?? "";
