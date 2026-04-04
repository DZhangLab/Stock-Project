package com.summer.stockproject.service;

import com.summer.stockproject.dao.CompanyNewsAiSummaryRepository;
import com.summer.stockproject.entity.CompanyNewsAiSummary;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.sql.Date;
import java.time.LocalDate;

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

    @Override
    public CompanyNewsAiSummary getBySymbolAsOfDate(String symbol, String targetDate) {
        if (symbol == null || targetDate == null) {
            return null;
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return null;
        }
        Date sqlDate = Date.valueOf(LocalDate.parse(targetDate));

        // Step 1: prefer an exact calendar-day match
        CompanyNewsAiSummary exact = repository
                .findTopBySymbolAndAnalysisDate(normalized, sqlDate);
        if (exact != null) {
            return exact;
        }

        // Step 2: fallback — most recent summary before targetDate
        return repository
                .findTopBySymbolAndAnalysisDateLessThanOrderByAnalysisDateDesc(
                        normalized, sqlDate);
    }
}
