package com.summer.stockproject.service;

import com.summer.stockproject.entity.EarningsAiAnalysis;

public interface EarningsAiAnalysisService {
    EarningsAiAnalysis getLatestBySymbol(String symbol);
}
