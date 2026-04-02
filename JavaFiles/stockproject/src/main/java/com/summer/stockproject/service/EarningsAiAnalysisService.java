package com.summer.stockproject.service;

import com.summer.stockproject.entity.EarningsAiAnalysis;

import java.util.List;

public interface EarningsAiAnalysisService {
    EarningsAiAnalysis getLatestBySymbol(String symbol);

    List<String> getPeriodsBySymbol(String symbol);

    EarningsAiAnalysis getBySymbolAndPeriod(String symbol, String period);
}
