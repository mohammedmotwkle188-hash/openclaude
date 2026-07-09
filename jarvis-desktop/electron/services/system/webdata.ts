import type { NewsHeadline, WeatherSnapshot } from "../../../shared/types";
import { getApiKey, getSettings } from "../../store";

export async function fetchWeather(location?: string): Promise<WeatherSnapshot> {
  const loc = location?.trim() || getSettings().weatherLocation;
  const apiKey = getApiKey("openweather");
  if (!apiKey) {
    throw new Error("Add an OpenWeather API key in Settings to enable live weather.");
  }
  const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(loc)}&units=metric&appid=${apiKey}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Weather lookup failed (${res.status}) for "${loc}".`);
  const data = (await res.json()) as any;
  return {
    location: data.name ?? loc,
    tempC: Math.round(data.main?.temp ?? 0),
    condition: data.weather?.[0]?.description ?? "unknown",
    humidityPercent: data.main?.humidity ?? 0,
    updatedAt: Date.now(),
  };
}

export async function fetchNews(): Promise<NewsHeadline[]> {
  const apiKey = getApiKey("newsapi");
  if (!apiKey) {
    throw new Error("Add a NewsAPI key in Settings to enable live headlines.");
  }
  const url = `https://newsapi.org/v2/top-headlines?language=en&pageSize=8&apiKey=${apiKey}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`News lookup failed (${res.status}).`);
  const data = (await res.json()) as any;
  return (data.articles ?? []).map((a: any, i: number) => ({
    id: String(i),
    title: a.title,
    source: a.source?.name ?? "unknown",
    url: a.url,
    publishedAt: new Date(a.publishedAt).getTime(),
  }));
}

export async function fetchStockQuote(symbol: string): Promise<string> {
  // Stooq offers free, keyless end-of-day/delayed quotes — good enough for a HUD readout
  // without requiring the user to provision a brokerage API key.
  const res = await fetch(`https://stooq.com/q/l/?s=${encodeURIComponent(symbol)}&f=sd2t2ohlcv&h&e=csv`);
  if (!res.ok) throw new Error("Stock lookup failed.");
  const csv = await res.text();
  const [, row] = csv.trim().split("\n");
  const cols = row?.split(",") ?? [];
  const close = cols[6];
  if (!close || close === "N/D") throw new Error(`No quote found for "${symbol}".`);
  return `${symbol.toUpperCase()}: ${close}`;
}

export async function fetchCryptoPrice(symbol: string): Promise<string> {
  const id = symbol.toLowerCase();
  const res = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${encodeURIComponent(id)}&vs_currencies=usd`);
  if (!res.ok) throw new Error("Crypto lookup failed.");
  const data = (await res.json()) as Record<string, { usd: number }>;
  const price = data[id]?.usd;
  if (price === undefined) throw new Error(`No price found for "${symbol}". Try the full CoinGecko id (e.g. "bitcoin").`);
  return `${symbol.toUpperCase()}: $${price.toLocaleString()}`;
}
