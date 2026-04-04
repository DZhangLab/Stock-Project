# News Date-Alignment Design

## Overview

The stock detail page aligns **news articles** and **AI news summaries** with
the date range currently shown on the stock chart, using **calendar-day
semantics** so the news context always matches the chart window.

---

## Timezone Assumption

All date/time boundaries use **US Eastern Time (ET)**, consistent with the
rest of the stock detail page (chart timestamps, intraday session
09:30-16:00, etc.).  The `published_at` column in `company_news` stores
wall-clock ET timestamps; the `analysis_date` column in
`company_news_ai_summary` stores calendar dates in ET.

---

## Core Concepts

### Date-Alignment Parameters

Every stock detail page view is characterised by four values:

| Parameter      | Type       | Description                                          |
|----------------|------------|------------------------------------------------------|
| `symbol`       | String     | Stock ticker (e.g. `AAPL`)                           |
| `rangeStart`   | LocalDate  | First calendar date of the chart window              |
| `rangeEnd`     | LocalDate  | Last calendar date of the chart window               |
| `asOfDate`     | LocalDate  | Equals `rangeEnd`; target date for AI summary lookup |

---

## Rules

### A. Raw News List — Calendar-Day Filtering

News articles are included when their `published_at` falls within the
**calendar-day window** of the chart range.

```
from = rangeStart 00:00:00 ET
to   = rangeEnd   23:59:59 ET
```

Spring Data query (inclusive on both sides):

```
findTop20BySymbolAndPublishedAtBetweenOrderByPublishedAtDesc(symbol, from, to)
```

#### Single-day view

`rangeStart = rangeEnd = selectedDate`

→ shows news published on that calendar day (00:00:00 through 23:59:59 ET).

#### Multi-day view

`rangeStart` and `rangeEnd` span the chart window.

→ shows news published within [rangeStart 00:00:00, rangeEnd 23:59:59] ET.

### B. News AI Summary — Exact-Day-First with Fallback

1. **Exact match:** find a summary where `analysis_date = targetDate`.
2. **Fallback:** if no exact match exists, return the most recent summary
   where `analysis_date < targetDate`.

For single-day charts, `targetDate = selectedDate`.
For multi-day charts, `targetDate = rangeEnd`.

This means historical chart views never pull a summary from a later date.
The fallback ensures the card still shows useful context even when no
summary was generated for the exact target day.

---

## Old Rule vs New Rule

### Raw news

| Aspect       | Old rule (market-close boundary)                           | New rule (calendar-day)                     |
|--------------|------------------------------------------------------------|---------------------------------------------|
| From         | `(rangeStart − 1 day) 16:00:01 ET`                        | `rangeStart 00:00:00 ET`                    |
| To           | `rangeEnd 16:00:00 ET`                                     | `rangeEnd 23:59:59 ET`                      |
| After-hours  | News after 16:00 on rangeEnd excluded (assigned to next day) | Included (belongs to same calendar day)     |
| Pre-market   | News before 16:00 previous day included (assigned to rangeStart) | Excluded (belongs to previous calendar day) |

### News AI summary

| Aspect       | Old rule                                     | New rule                                      |
|--------------|----------------------------------------------|-----------------------------------------------|
| Lookup       | `analysis_date <= asOfDate` (nearest earlier) | Exact match first, then nearest earlier        |
| Fallback     | Implicit (single <= query)                   | Explicit two-step: exact → nearest `< target` |

---

## API Contract

### News Articles (server-side rendered)

Fetched by `StockController`, passed to the Thymeleaf template.

```
CompanyNewsService.getNewsBySymbolAndDateRange(symbol, rangeStart, rangeEnd)
```

### AI News Summary (client-side fetch)

```
GET /api/financials/news-ai/by-date?symbol=AAPL&asOfDate=2026-04-01
```

| Parameter  | Required | Default | Description                                       |
|------------|----------|---------|---------------------------------------------------|
| `symbol`   | no       | AAPL    | Stock ticker                                      |
| `asOfDate` | no       | (none)  | yyyy-MM-dd; falls back to absolute latest if absent |

Lookup order:
1. `analysis_date = asOfDate` (exact match)
2. Most recent `analysis_date < asOfDate` (fallback)
3. Absolute latest (when `asOfDate` is absent)

The old `/news-ai/latest` endpoint remains for backward compatibility.

---

## Examples

### a) Chart on 2026-04-01 (single day)

```
rangeStart = 2026-04-01
rangeEnd   = 2026-04-01
asOfDate   = 2026-04-01

News query window : [2026-04-01 00:00:00, 2026-04-01 23:59:59] ET
AI summary        : analysis_date = 2026-04-01
                    fallback → latest analysis_date < 2026-04-01
```

### b) Chart range 2026-03-27 to 2026-04-02 (multi-day)

```
rangeStart = 2026-03-27
rangeEnd   = 2026-04-02
asOfDate   = 2026-04-02

News query window : [2026-03-27 00:00:00, 2026-04-02 23:59:59] ET
AI summary        : analysis_date = 2026-04-02
                    fallback → latest analysis_date < 2026-04-02
```

---

## Optional Future Enhancement: market_date Column

The calendar-day rule is simple and intuitive.  If a more precise
market-session alignment is ever needed (e.g. after-hours news assigned to
the next trading day), a `market_date DATE` column can be added to
`company_news` with an index on `(symbol, market_date)` and a back-fill
migration.  This is not required for the current calendar-day design.
