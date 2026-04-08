package com.summer.stockproject.service;

import com.summer.stockproject.entity.CompanyNews;

import java.util.List;

public interface CompanyNewsService {
    List<CompanyNews> getRecentNews(String symbol);

    /**
     * Return up to 20 news items for the given symbol whose published_at
     * falls within the calendar-day window [rangeStart, rangeEnd].
     *
     * Calendar-day rule (all times in ET):
     *   from = rangeStart 00:00:00
     *   to   = rangeEnd   23:59:59
     *
     * @param symbol     stock ticker (e.g. "AAPL")
     * @param rangeStart inclusive start date, yyyy-MM-dd
     * @param rangeEnd   inclusive end date, yyyy-MM-dd
     */
    List<CompanyNews> getNewsBySymbolAndDateRange(String symbol,
                                                   String rangeStart,
                                                   String rangeEnd);
}
