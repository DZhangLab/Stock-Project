package com.summer.stockproject.service;

import com.summer.stockproject.entity.DailyQuote;

import java.util.List;

public interface DailyQuoteService {

    /**
     * Find daily quotes for a symbol within a date range.
     *
     * @param symbol    API-format symbol (e.g. "AAPL", "BRK.B")
     * @param startDate ISO date string "yyyy-MM-dd"
     * @param endDate   ISO date string "yyyy-MM-dd"
     * @return quotes ordered by datetime ascending
     */
    List<DailyQuote> findBySymbolAndDateRange(String symbol, String startDate, String endDate);

    /**
     * Get the most recent date with data for a symbol.
     *
     * @param symbol API-format symbol
     * @return ISO date string "yyyy-MM-dd", or null if no data exists
     */
    String getLatestDateForSymbol(String symbol);
}
