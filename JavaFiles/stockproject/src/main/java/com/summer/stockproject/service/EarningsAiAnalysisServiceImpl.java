package com.summer.stockproject.service;

import com.summer.stockproject.dao.EarningsAiAnalysisRepository;
import com.summer.stockproject.entity.EarningsAiAnalysis;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;

@Service
public class EarningsAiAnalysisServiceImpl implements EarningsAiAnalysisService {

    private final EarningsAiAnalysisRepository repository;

    @Autowired
    public EarningsAiAnalysisServiceImpl(EarningsAiAnalysisRepository repository) {
        this.repository = repository;
    }

    @Override
    public EarningsAiAnalysis getLatestBySymbol(String symbol) {
        if (symbol == null) {
            return null;
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return null;
        }
        return repository.findTopBySymbolOrderByFiscalPeriodLabelDesc(normalized);
    }

    @Override
    public List<String> getPeriodsBySymbol(String symbol) {
        if (symbol == null) {
            return Collections.emptyList();
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return Collections.emptyList();
        }
        List<String> periods = repository.findPeriodsBySymbol(normalized);
        return periods != null ? periods : Collections.emptyList();
    }

    @Override
    public EarningsAiAnalysis getBySymbolAndPeriod(String symbol, String period) {
        if (symbol == null || period == null) {
            return null;
        }
        String normalizedSymbol = symbol.trim().toUpperCase();
        String normalizedPeriod = stripFyPrefix(period.trim());
        if (normalizedSymbol.isEmpty() || normalizedPeriod.isEmpty()) {
            return null;
        }
        return repository.findBySymbolAndFiscalPeriodLabel(normalizedSymbol, normalizedPeriod);
    }

    /**
     * Strip the "FY" prefix so queries match the DB canonical format (e.g. "2025Q1").
     */
    private static String stripFyPrefix(String period) {
        if (period.toUpperCase().startsWith("FY")) {
            return period.substring(2);
        }
        return period;
    }
}
