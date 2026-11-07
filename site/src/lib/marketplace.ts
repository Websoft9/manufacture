import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";

const PLATFORM_KEYS = [
  "aliyun",
  "alibabacloud",
  "huaweiyun",
  "huaweicloud",
  "azure",
  "azure-vmlab",
  "aws",
] as const;

export type PlatformKey = (typeof PLATFORM_KEYS)[number];
export type AppStatus = "listed" | "unlisted" | "outside";

export interface StoreConfig {
  label: string;
  url: string;
}

interface PlatformConfig {
  key: string;
  label: string;
  description: string;
  urlTemplate?: string;
  stores?: StoreConfig[];
  overviewKey?: string;
}

interface ProductPlatformConfig extends PlatformConfig {
  key: PlatformKey;
  urlTemplate: string;
}

interface RouteRule {
  prefix: string;
  platform: string;
}

interface PlatformRoute {
  default: string;
  rules?: RouteRule[];
}

interface MarketplaceConfig {
  version: number;
  sources: {
    offer: string;
  };
  platforms: PlatformConfig[];
  routing: Record<string, PlatformRoute>;
}

interface AppConfig {
  sources: {
    catalog: string;
    versions?: string;
  };
  multi_version_apps?: string[];
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
  key: string;
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

export interface CatalogCategory {
  key?: string;
  title?: string;
  catalogCollection?: {
    items?: CatalogCategory[];
  };
}

export interface CatalogProduct {
  key: string;
  trademark?: string;
  summary?: string;
  overview?: string;
  description?: string;
  websiteurl?: string;
  keywords?: string[] | string;
  usecases?: string[] | string;
  useCases?: string[] | string;
  distribution?: Array<{ key?: string; value?: string[] }>;
  logo?: { imageurl?: string };
  screenshots?: Array<{ id?: string; key?: string; value?: string }>;
  catalogCollection?: { items?: CatalogCategory[] };
  relatedAppsCollection?: {
    items?: Array<{ key?: string; trademark?: string }>;
  };
}

function findRepoFile(start: string, relativePath: string): string {
  let directory = start;
  while (true) {
    const candidate = join(directory, relativePath);
    if (existsSync(candidate)) return candidate;
    const parent = dirname(directory);
    if (parent === directory) {
      throw new Error(`Unable to locate ${relativePath}`);
    }
    directory = parent;
  }
}

const CONFIG_PATH =
  process.env.MK_CONFIG_PATH ??
  findRepoFile(process.cwd(), join("config", "marketplace.json"));
const CONFIG = JSON.parse(readFileSync(CONFIG_PATH, "utf8")) as MarketplaceConfig;

const APP_CONFIG_PATH =
  process.env.MK_APP_CONFIG_PATH ?? join(dirname(CONFIG_PATH), "app.json");
const APP_CONFIG = JSON.parse(readFileSync(APP_CONFIG_PATH, "utf8")) as AppConfig;

function isProductPlatform(platform: PlatformConfig): platform is ProductPlatformConfig {
  return (
    typeof platform.urlTemplate === "string" &&
    (PLATFORM_KEYS as readonly string[]).includes(platform.key)
  );
}

for (const platform of CONFIG.platforms) {
  if (platform.urlTemplate && !isProductPlatform(platform)) {
    throw new Error(`Unknown product platform: ${platform.key}`);
  }
  if (platform.urlTemplate && !platform.urlTemplate.includes("{code}")) {
    throw new Error(`Platform ${platform.key} URL template must include {code}`);
  }
  for (const store of platform.stores ?? []) {
    if (!store.url.startsWith("https://")) {
      throw new Error(`Platform ${platform.key} store URL must use HTTPS`);
    }
  }
}

const ALL_PLATFORM_KEYS = new Set(CONFIG.platforms.map((platform) => platform.key));
for (const [source, route] of Object.entries(CONFIG.routing)) {
  if (!ALL_PLATFORM_KEYS.has(route.default)) {
    throw new Error(`Unknown default platform for ${source}: ${route.default}`);
  }
  for (const rule of route.rules ?? []) {
    if (!ALL_PLATFORM_KEYS.has(rule.platform)) {
      throw new Error(`Unknown routed platform for ${source}: ${rule.platform}`);
    }
  }
}

const ENV = (
  globalThis as { process?: { env?: Record<string, string | undefined> } }
).process?.env;

export const OFFER_URL = ENV?.MK_OFFER_URL ?? CONFIG.sources.offer;
export const CATALOG_URL = ENV?.MK_CATALOG_URL ?? APP_CONFIG.sources.catalog;

const PRODUCT_PLATFORMS = CONFIG.platforms.filter(isProductPlatform);
const OVERVIEW_PLATFORMS = CONFIG.platforms.filter(
  (platform) => (platform.overviewKey ?? platform.key) === platform.key,
);

export const PLATFORMS = PRODUCT_PLATFORMS;
const PLATFORM_URL_TEMPLATES = Object.fromEntries(
  PRODUCT_PLATFORMS.map((platform) => [platform.key, platform.urlTemplate]),
) as Record<PlatformKey, string>;

function isProductPlatformKey(value: string): value is PlatformKey {
  return (PLATFORM_KEYS as readonly string[]).includes(value);
}

function routePlatform(sourceKey: string, code: string): PlatformKey | undefined {
  const route = CONFIG.routing[sourceKey.toLowerCase()];
  if (!route) return undefined;

  const rule = (route.rules ?? []).find((candidate) =>
    code.toLowerCase().startsWith(candidate.prefix.toLowerCase()),
  );
  const target = rule?.platform ?? route.default;
  return isProductPlatformKey(target) ? target : undefined;
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
  for (const platform of PRODUCT_PLATFORMS) {
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
    platformCounts: OVERVIEW_PLATFORMS.map((platform) => {
      const groupedKeys = CONFIG.platforms
        .filter(
          (candidate) =>
            (candidate.overviewKey ?? candidate.key) === platform.key,
        )
        .map((candidate) => candidate.key);

      return {
        key: platform.key,
        label: platform.label,
        description: platform.description,
        stores: platform.stores ?? [],
        count: listed.filter((row) =>
          groupedKeys.some(
            (key) =>
              isProductPlatformKey(key) && row.links[key].length > 0,
          ),
        ).length,
      };
    }),
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
  catalog: CatalogProduct[];
}> {
  const [offers, catalog] = await Promise.all([
    fetchJson<Offer[]>(OFFER_URL),
    loadCatalogProducts(),
  ]);
  if (!Array.isArray(offers) || !Array.isArray(catalog)) {
    throw new Error("Marketplace data sources must return JSON arrays");
  }

  const rows = buildRows(offers, catalog);
  return { rows, stats: calculateStats(rows), generatedAt: new Date(), catalog };
}

export async function loadCatalogProducts(): Promise<CatalogProduct[]> {
  const catalog = await fetchJson<CatalogProduct[]>(CATALOG_URL);
  if (!Array.isArray(catalog)) {
    throw new Error("The product catalog must return a JSON array");
  }
  return catalog.filter((product) => Boolean(product.key));
}
