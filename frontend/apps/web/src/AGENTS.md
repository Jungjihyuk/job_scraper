# FRONTEND — React/TS Dashboard (Feature-Sliced Design)

## OVERVIEW

React 19 + Vite + TypeScript dashboard for job scraping management. Feature-Sliced Design architecture.

## STRUCTURE

```
src/
├── main.tsx             # React root render
├── app/                 # App shell
│   ├── index.tsx        # App component (BrowserRouter + providers)
│   ├── router/          # Route definitions (lazy-loaded pages)
│   ├── providers/       # Context providers (minimal wrapper, extensible)
│   └── styles/          # Global CSS + Tailwind
├── pages/               # Route-level components (one dir per page)
│   ├── scraping/        # Scraping management — uses dashboard + scraping entities
│   ├── deadline/        # Deadline tracking — uses job-posting entity (filters)
│   ├── recent/          # Recent postings — uses job-posting entity
│   └── statistics/      # Analytics — uses statistics + job-posting entities, recharts
├── entities/            # Domain entities (FSD layer)
│   ├── dashboard/       # useDashboardStats hook + fetchDashboardStats API
│   ├── job-posting/     # useDeadlineJobs, useRecentJobs, useFilterOptions + JobCard UI + 7 fetch APIs
│   ├── scraping/        # useScrapingSocket hook + start/stop/status APIs + SCRAPER_TYPES/JOB_OPTIONS
│   └── statistics/      # 5 useStatistics hooks + 7 fetch APIs + chart transforms
├── shared/              # Shared utilities (FSD layer)
│   ├── api/             # getJson/postJson client, useWebSocket hook, shared types
│   ├── config/          # API_BASE_URL from env
│   ├── lib/             # Utility functions
│   └── ui/              # LoadingSpinner, ErrorMessage, EmptyState
└── widgets/
    └── layout/          # App layout (sidebar nav + header)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new page | `pages/{name}/` | Export page component, lazy-load in `app/router/` |
| Add entity | `entities/{name}/` | Create `model/` (types+hooks) + `api/` (fetch functions) |
| Add shared component | `shared/ui/` | Export from barrel `index.ts` |
| Modify API client | `shared/api/client.ts` | `getJson()`/`postJson()` wrappers with base URL |
| Change layout | `widgets/layout/` | Sidebar nav links, header |
| Add route | `app/router/index.tsx` | Lazy import + `<Route>` entry |
| Add API type | `shared/api/types.ts` | All API response/request types live here |
| Add chart transform | `entities/statistics/lib/transforms.ts` | `transformStackedBar`, `transformLineChart`, etc. |

## ENTITY → PAGE MAPPING

| Page | Entities Used | Key Hooks |
|------|--------------|-----------|
| ScrapingPage | dashboard, scraping | `useDashboardStats`, `useScrapingSocket` |
| DeadlinePage | job-posting | `useDeadlineJobs`, `useFilterOptions` |
| RecentPage | job-posting | `useRecentJobs` |
| StatisticsPage | statistics, job-posting | `useSpecialtyByLocation`, `usePostingTrends`, `useDomainDistribution`, `useTechnologyTrends`, `useFilterOptions` |

## CONVENTIONS

- **FSD layers**: app → pages → entities → shared (import only downward)
- **All imports relative** — no tsconfig path aliases
- **Barrel exports** via `index.ts` in each module
- **Lazy loading** all pages via `React.lazy()` + `Suspense`
- **Styling**: Tailwind CSS 3 + PostCSS
- **Charts**: recharts library
- **API proxy**: Vite proxies `/api` and `/ws` to backend (port 8000) via `vite.config.ts`
- **No state management library** — custom hooks + prop drilling
- **WebSocket**: `useWebSocket` hook in `shared/api/` — `useScrapingSocket` wraps it for scraping events
