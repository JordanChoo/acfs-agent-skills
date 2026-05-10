---
name: astro-site
description: >-
  Discipline for Astro v5 static-site projects (Tailwind v4, MDX, content
  collections, sitemap, RSS). Use when the repo has astro.config.{mjs,ts},
  src/content.config.ts, or `astro` in deps; when adding content collections,
  pages, redirects, or sitemap entries; when migrating a site from WordPress
  or another platform; when debugging Astro build/check failures. Encodes the
  canonical layout, content schema patterns, sitemap filter, redirect handling,
  and Tailwind v4 conventions used across this user's Astro template lineage.
---

# astro-site

Decision logic for Astro static-site projects in this environment. Goal: keep new sites consistent with the `astro-template` lineage and avoid the recurring SEO/build traps.

## Triggers

Load this skill when ANY of:
- Files: `astro.config.{mjs,ts,js}`, `src/content.config.ts`, `src/content/`, `*.astro` files
- Deps: `astro`, `@astrojs/mdx`, `@astrojs/sitemap`, `@astrojs/rss`, `@tailwindcss/vite`, `astro-custom-toc`
- User mentions: astro, content collection, sitemap, MDX, RSS, Tailwind v4, WP migration, redirect, getCollection, `<Image>`

## Canonical stack signature

Astro projects in this lineage share a tight stack — confirm before assuming:

```
"astro": "^5.x"
"@astrojs/mdx", "@astrojs/sitemap", "@astrojs/rss"   # always
"@tailwindcss/vite", "tailwindcss": "^4.x"            # Tailwind v4 via Vite plugin (NOT v3 PostCSS)
"astro-custom-toc"                                    # usually
"zod": "^4.x"                                         # content schemas
"@astrojs/check"                                      # type-check
```

If the project has `@astrojs/cloudflare`, `@astrojs/netlify`, `@astrojs/vercel`, or `@astrojs/node`, it's a server-rendered Astro project — most rules below still apply, but check `output:` in `astro.config.mjs` first.

## Canonical `src/` layout

```
src/
  components/         # .astro / .ts components
  config/             # site config (nav, brand, footer)
  content/
    blog/
    services/         # or locations/, team/, projects/, etc.
    team/             # authors, referenced from blog via reference('team')
  content.config.ts   # Zod schemas for every collection
  data/               # static data files (.ts/.json)
  layouts/            # base + page-type layouts
  pages/              # routes
  styles/
  utils/
public/               # static assets, robots.txt, favicon
prd/PRD.md            # product requirements (template convention)
```

When adding a new content type, **add the schema to `src/content.config.ts` first**, then add the directory + first entry. Astro's content layer fails the build if the directory exists but the schema doesn't.

---

## Playbooks

### Adding a content collection

1. Edit `src/content.config.ts` — add a `defineCollection` block with `loader: glob(...)` and a Zod schema.
2. Use `reference('<other-collection>')` for cross-refs (e.g., blog post → team author).
3. Use `z.coerce.date()` for `pubDate` so frontmatter strings parse correctly.
4. Make optional fields explicit with `.optional()` — Astro v5 is strict; missing required fields fail the build.
5. Run `npm run check` (= `astro check`) after schema changes; it catches schema/data mismatches before build.
6. Reference: `astro-template/src/content.config.ts` is the canonical example (blog + team with `reference()`).

### Adding a page or route

1. New page → `src/pages/<route>.astro` or `src/pages/<route>/index.astro`. Astro routing is filesystem-based.
2. If the page should be excluded from the sitemap (thank-you, 404, paginated dups), update the `sitemap()` filter in `astro.config.mjs` — see "Sitemap discipline" below.
3. If replacing or moving a path, **add a redirect** in `astro.config.mjs` (`redirects: { '/old': '/new' }`). Don't rely on 404s.
4. For dynamic routes (`[slug].astro`), implement `getStaticPaths()` and pull from collections via `getCollection('<name>')`.

### Sitemap discipline (recurring trap)

Every project in this lineage filters the sitemap. Pattern:

```js
sitemap({
  filter: (page) => {
    const path = new URL(page).pathname;
    // Paginated dup pages
    if (/\/blog\/\d+\/$/.test(path)) return false;
    if (/\/blog\/tags\/[^/]+\/\d+\/$/.test(path)) return false;
    if (/\/blog\/categories\/[^/]+\/\d+\/$/.test(path)) return false;
    // Noindex pages
    if (path === '/thank-you/') return false;
    if (path === '/404/') return false;
    return true;
  },
  changefreq: 'weekly',
  priority: 0.7,
  lastmod: new Date(),
})
```

When adding paginated routes (tags, categories, year archives), extend the filter at the same time. Otherwise the sitemap fills with `/blog/2/`, `/blog/3/`, etc. and dilutes SEO.

### WordPress migration (recurring use case)

Two projects in this lineage migrated from WordPress (`arp-astro`, `gkn-static`). The pattern:

1. **Redirects** — every old WP URL needs a `redirects:` entry in `astro.config.mjs`. Common WP path patterns: `/feed`, `/feed/atom`, `/?p=N`, `/category/...`, `/tag/...`, `/<slug>` (WP rewrite rules), and any `/service/...` or `/location/...` singular paths.
2. **Trailing slash** — set `trailingSlash: 'always'` if the WP site used trailing slashes, to keep canonical URLs stable. Mismatched trailing slashes break inbound links and search rankings.
3. **Migration scripts** — `gkn-static` has `scripts/migrate/{parse,transform,extract,media,redirects,validate}.ts` driven by `npm run migrate:all`. If you're starting a new WP migration, copy that script structure rather than improvising.
4. **Validate before launch**: run a crawl of the old site, diff against the new sitemap, confirm every old URL either resolves or redirects.

### Tailwind v4 caveats (this lineage is on v4)

- Plugin is `@tailwindcss/vite`, NOT the v3 PostCSS plugin. Don't add `postcss.config.js`.
- Config lives in CSS via `@theme { ... }` blocks, not `tailwind.config.js`. Some agents reflexively add a v3-style config file — don't.
- `@tailwindcss/typography` works in v4 but is configured differently — check existing `src/styles/` before adding.
- Class names mostly transfer from v3, but some utility names changed (e.g., shadow scale). When porting v3 examples, verify in v4 docs.

### Images

Astro v5's `astro:assets` is the right tool — `import { Image } from 'astro:assets'` and pass an imported asset (not a string path). For collection-frontmatter images, use `image()` in the Zod schema:

```ts
schema: ({ image }) => z.object({
  cover: image(),
  ...
})
```

This gives you `width`/`height`/`format` automatically and lets the build pipeline optimize.

### Build, check, and tests

- `npm run check` (= `astro check`) — type-checks `.astro` + content schemas. Run before every PR.
- `npm run build` — strict; fails on broken collection refs, missing required frontmatter, broken links inside MDX.
- `npm run test` — Vitest with `happy-dom`; mostly unit tests for utils, not page rendering.
- `npm run dev` — HMR. Content schema changes sometimes need a full restart, not just HMR.

### Beads (issue tracking) — note the version

These projects use `bd` (legacy beads), not `br` (beads_rust). If updating workflow docs or commands, the `bd-to-br-migration` skill applies — but **don't migrate unless explicitly asked**, because the rest of the project's tooling expects `bd`.

---

## Red flags — stop and ask

- Adding `tailwind.config.js` or `postcss.config.js` — this is Tailwind v4, configure in CSS instead
- A new content directory under `src/content/` without a matching `defineCollection` in `src/content.config.ts`
- New paginated routes without sitemap filter updates
- Replacing/renaming a page without adding a redirect
- Bare-string image paths (`<img src="/photos/foo.jpg">`) in places where `astro:assets` should be used — loses optimization
- Switching `output:` from `static` to `server` without an adapter and matching deploy plan
- Adding a server-side feature (API routes, dynamic SSR) to a project that has no adapter and no deploy story for SSR

---

## What to read first in an unfamiliar Astro repo

1. `astro.config.mjs` — site URL, integrations, redirects, sitemap filter, output mode
2. `src/content.config.ts` — every collection schema; check before editing any markdown frontmatter
3. `package.json` scripts — confirm `dev`/`build`/`check`/`test` are the conventional names
4. `src/layouts/` — base layouts wrap every page; SEO/meta lives here
5. `src/config/` — site-wide config (nav, footer, brand)
6. `prd/PRD.md` if present — product requirements for this specific site
7. `CLAUDE.md` / `AGENTS.md` for project-specific overrides
