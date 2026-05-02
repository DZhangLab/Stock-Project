package com.summer.stockproject.service;

import com.summer.stockproject.entity.DailyVolatility;

import java.util.List;

public interface DailyVolatilityService {

    /**
     * Returns the latest daily_volatility row for the symbol, or null
     * if the symbol has no rows.
     */
    DailyVolatility getLatestBySymbol(String symbol);

    /**
     * Returns the most recent {@code days} rows for the symbol, sorted
     * ascending by as_of_date so the result is chart-friendly.  The
     * {@code days} parameter is bounded to a sensible range to prevent
     * unbounded queries.
     */
    List<DailyVolatility> getRecentBySymbol(String symbol, int days);
}
