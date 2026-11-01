import { defineConfig } from "astro/config";

const rawBase = (process.env.BASE_PATH ?? "/").trim();
const base =
  rawBase === "" || rawBase === "/"
    ? "/"
    : `/${rawBase.replace(/^\/+|\/+$/g, "")}/`;

export default defineConfig({
  output: "static",
  base,
  site: process.env.SITE_URL || undefined,
});
