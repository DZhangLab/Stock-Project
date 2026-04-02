package com.summer.stockproject.service;

import com.summer.stockproject.dao.EarningsCallSummaryRepository;
import com.summer.stockproject.entity.EarningsCallSummary;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class EarningsCallSummaryServiceImpl implements EarningsCallSummaryService {

    private final EarningsCallSummaryRepository repository;

    @Autowired
    public EarningsCallSummaryServiceImpl(EarningsCallSummaryRepository repository) {
        this.repository = repository;
    }

    @Override
    public EarningsCallSummary getLatestBySymbol(String symbol) {
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
    public EarningsCallSummary getBySymbolAndPeriod(String symbol, String period) {
        if (symbol == null || period == null) {
            return null;
        }
        String normalizedSymbol = symbol.trim().toUpperCase();
        String normalizedPeriod = period.trim().toUpperCase();
        if (normalizedPeriod.startsWith("FY")) {
            normalizedPeriod = normalizedPeriod.substring(2);
        }
        if (normalizedSymbol.isEmpty() || normalizedPeriod.isEmpty()) {
            return null;
        }
        return repository.findBySymbolAndFiscalPeriodLabel(normalizedSymbol, normalizedPeriod);
    }
}
