package com.summer.stockproject.service;

import com.summer.stockproject.entity.EarningsCallSummary;

public interface EarningsCallSummaryService {
    EarningsCallSummary getLatestBySymbol(String symbol);

    EarningsCallSummary getBySymbolAndPeriod(String symbol, String period);
}
