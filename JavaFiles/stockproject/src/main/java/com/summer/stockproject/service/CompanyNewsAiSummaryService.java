package com.summer.stockproject.service;

import com.summer.stockproject.entity.CompanyNewsAiSummary;

public interface CompanyNewsAiSummaryService {
    CompanyNewsAiSummary getLatestBySymbol(String symbol);

    /**
     * Calendar-day-aware lookup for the AI news summary.
     *
     * 1. Try exact match: analysis_date = targetDate.
     * 2. Fallback: most recent summary where analysis_date < targetDate.
     *
     * For single-day charts targetDate equals the selected date;
     * for multi-day charts targetDate equals rangeEnd.
     *
     * @param symbol     stock ticker
     * @param targetDate yyyy-MM-dd calendar day to match
     */
    CompanyNewsAiSummary getBySymbolAsOfDate(String symbol, String targetDate);
}
