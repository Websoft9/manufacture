import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";

const PLATFORM_KEYS = [
  "aliyun",
  "alibabacloud",
  "huaweiyun",
  "huaweicloud",
  "azure",
  "aws",
] as const;

export type PlatformKey = (typeof PLATFORM_KEYS)[number];
export type AppStatus = "listed" | "unlisted" | "outside";

export interface StoreConfig {
  label: string;
  url: string;
}

interface PlatformConfig {
  key: PlatformKey;
  label: string;
  description: string;
  urlTemplate: string;
  stores: StoreConfig[];
}

interface RouteRule {
  prefix: string;
  platform: PlatformKey;
}

interface PlatformRoute {
  default: PlatformKey;
  rules?: RouteRule[];
}

interface MarketplaceConfig {
  version: number;
  sources: {
    offer: string;
    catalog: string;
  };
  platforms: PlatformConfig[];
  routing: Record<string, PlatformRoute>;
}

export interface ProductLink {
  platform: PlatformKey;
  code: string;
  url: string;
}

export interface AppRow {
  key: string;
  name: string;
  links: Record<PlatformKey, ProductLink[]>;
  inCatalog: boolean;
  hasLinks: boolean;
}

export interface PlatformCount {
  key: PlatformKey;
  label: string;
  description: string;
  stores: StoreConfig[];
  count: number;
}

export interface MarketplaceStats {
  catalog: number;
  listed: number;
  unlisted: number;
  outside: number;
  platformCounts: PlatformCount[];
}

interface Offer {
  id?: string;
  type?: string;
  applications?: string[];
  productID?: Record<string, string[] | undefined>;
}

interface CatalogProduct {
  key?: string;
  trademark?: string;
}

function findConfig(start: string): string {
  let directory = start;
  while (true) {
    const candidate = join(directory, "config", "marketplace.json");
    if (existsSync(candidate)) return candidate;
    const parent = dirname(directory);
    if (parent === directory) {
      throw new Error("Unable to locate config/marketplace.json");
    }
    directory = parent;
  }
}

const CONFIG_PATH = process.env.MK_CONFIG_PATH ?? findConfig(process.cwd());
const CONFIG = JSON.parse(readFileSync(CONFIG_PATH, "utf8")) as MarketplaceConfig;

for (const platform of CONFIG.platforms) {
  if (!PLATFORM_KEYS.includes(platform.key)) {
    throw new Error(`Unknown marketplace platform: ${platform.key}`);
  }
  if (!platform.urlTemplate.includes("{code}")) {
    throw new Error(`Platform ${platform.key} URL template must include {code}`);
  }
  for (const store of platform.stores ?? []) {
    if (!store.url.startsWith("https://")) {
      throw new Error(`Platform ${platform.key} store URL must use HTTPS`);
    }
  }
}

for (const [source, route] of Object.entries(CONFIG.routing)) {
  if (!PLATFORM_KEYS.includes(route.default)) {
    throw new Error(`Unknown default platform for ${source}: ${route.default}`);
  }
  for (const rule of route.rules ?? []) {
    if (!PLATFORM_KEYS.includes(rule.platform)) {
      throw new Error(`Unknown routed platform for ${source}: ${rule.platform}`);
    }
  }
}

const ENV = (
  globalThis as { process?: { env?: Record<string, string | undefined> } }
).process?.env;

export const OFFER_URL = ENV?.MK_OFFER_URL ?? CONFIG.sources.offer;
export const CATALOG_URL = ENV?.MK_CATALOG_URL ?? CONFIG.sources.catalog;

export const PLATFORMS = CONFIG.platforms;
const PLATFORM_URL_TEMPLATES = Object.fromEntries(
  PLATFORMS.map((platform) => [platform.key, platform.urlTemplate]),
) as Record<PlatformKey, string>;

function routePlatform(sourceKey: string, code: string): PlatformKey | undefined {
  const route = CONFIG.routing[sourceKey.toLowerCase()];
  if (!route) return undefined;

  const rule = (route.rules ?? []).find((candidate) =>
    code.toLowerCase().startsWith(candidate.prefix.toLowerCase()),
  );
  return rule?.platform ?? route.default;
}

function productLink(platformKey: string, code: string): ProductLink | undefined {
  const platform = routePlatform(platformKey, code);
  if (!platform) return undefined;

  const template = PLATFORM_URL_TEMPLATES[platform];
  if (!template) return undefined;
  return { platform, code, url: template.replace(/\{code\}/g, code) };
}

function emptyLinks(): Record<PlatformKey, ProductLink[]> {
  const links = {} as Record<PlatformKey, ProductLink[]>;
  for (const platform of PLATFORMS) {
    links[platform.key] = [];
  }
  return links;
}

export function buildRows(offers: Offer[], catalog: CatalogProduct[]): AppRow[] {
  const catalogByKey = new Map(
    catalog
      .filter((item): item is CatalogProduct & { key: string } => Boolean(item.key))
      .map((item) => [item.key, item]),
  );
  const offerLinks = new Map<string, Record<PlatformKey, ProductLink[]>>();

  for (const offer of offers) {
    if (offer.type !== "app") continue;
    const key = offer.id ?? offer.applications?.[0];
    if (!key) continue;

    const links = offerLinks.get(key) ?? emptyLinks();
    for (const [platformKey, codes] of Object.entries(offer.productID ?? {})) {
      if (!Array.isArray(codes)) continue;
      for (const rawCode of codes) {
        if (!rawCode) continue;
        const link = productLink(platformKey, String(rawCode));
        if (!link) continue;
        const entries = links[link.platform];
        if (!entries.some((entry) => entry.code === link.code && entry.url === link.url)) {
          entries.push(link);
        }
      }
    }
    offerLinks.set(key, links);
  }

  return [...new Set([...catalogByKey.keys(), ...offerLinks.keys()])]
    .map((key) => {
      const catalogItem = catalogByKey.get(key);
      const links = offerLinks.get(key) ?? emptyLinks();
      return {
        key,
        name: catalogItem?.trademark || key,
        links,
        inCatalog: Boolean(catalogItem),
        hasLinks: Object.values(links).some((entries) => entries.length > 0),
      };
    })
    .sort(
      (a, b) =>
        a.name.localeCompare(b.name, undefined, { sensitivity: "base" }) ||
        a.key.localeCompare(b.key),
    );
}

export function rowStatus(row: AppRow): AppStatus {
  if (!row.inCatalog) return "outside";
  return row.hasLinks ? "listed" : "unlisted";
}

export function calculateStats(rows: AppRow[]): MarketplaceStats {
  const catalogRows = rows.filter((row) => row.inCatalog);
  const listed = catalogRows.filter((row) => row.hasLinks);
  const unlisted = catalogRows.filter((row) => !row.hasLinks);
  const outside = rows.filter((row) => !row.inCatalog);

  return {
    catalog: catalogRows.length,
    listed: listed.length,
    unlisted: unlisted.length,
    outside: outside.length,
    platformCounts: PLATFORMS.map((platform) => ({
      ...platform,
      count: listed.filter((row) => row.links[platform.key].length > 0).length,
    })),
  };
}

async function fetchJson<T>(url: string): Promise<T> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const response = await fetch(url, {
        headers: {
          Accept: "application/json",
          "User-Agent": "Websoft9-manufacture-site/1.0",
        },
        signal: AbortSignal.timeout(30_000),
      });
      if (!response.ok) {
        throw new Error(`Failed to load ${url}: ${response.status} ${response.statusText}`);
      }
      return (await response.json()) as T;
    } catch (error) {
      lastError = error;
      if (attempt < 3) {
        await new Promise((resolve) => setTimeout(resolve, attempt * 500));
      }
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error(`Failed to load ${url}`);
}

export async function loadMarketplaceData(): Promise<{
  rows: AppRow[];
  stats: MarketplaceStats;
  generatedAt: Date;
}> {
  const [offers, catalog] = await Promise.all([
    fetchJson<Offer[]>(OFFER_URL),
    fetchJson<CatalogProduct[]>(CATALOG_URL),
  ]);
  if (!Array.isArray(offers) || !Array.isArray(catalog)) {
    throw new Error("Marketplace data sources must return JSON arrays");
  }

  const rows = buildRows(offers, catalog);
  return { rows, stats: calculateStats(rows), generatedAt: new Date() };
}
