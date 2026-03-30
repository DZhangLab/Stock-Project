package com.summer.stockproject.service;

import com.summer.stockproject.entity.CompanyNewsAiSummary;

public interface CompanyNewsAiSummaryService {
    CompanyNewsAiSummary getLatestBySymbol(String symbol);
}
