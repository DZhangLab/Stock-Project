package com.summer.stockproject.service;

import com.summer.stockproject.dao.CompanyNewsAiSummaryRepository;
import com.summer.stockproject.entity.CompanyNewsAiSummary;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class CompanyNewsAiSummaryServiceImpl implements CompanyNewsAiSummaryService {

    private final CompanyNewsAiSummaryRepository repository;

    @Autowired
    public CompanyNewsAiSummaryServiceImpl(CompanyNewsAiSummaryRepository repository) {
        this.repository = repository;
    }

    @Override
    public CompanyNewsAiSummary getLatestBySymbol(String symbol) {
        if (symbol == null) {
            return null;
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return null;
        }
        return repository.findTopBySymbolOrderByUpdatedAtDescAnalysisDateDesc(normalized);
    }
}
