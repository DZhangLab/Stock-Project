package com.summer.stockproject.service;

import com.summer.stockproject.dao.EarningsEventOutcomeRepository;
import com.summer.stockproject.entity.EarningsEventOutcome;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;

@Service
public class EarningsEventOutcomeServiceImpl implements EarningsEventOutcomeService {

    private final EarningsEventOutcomeRepository repository;

    @Autowired
    public EarningsEventOutcomeServiceImpl(EarningsEventOutcomeRepository repository) {
        this.repository = repository;
    }

    @Override
    public List<EarningsEventOutcome> getBySymbol(String symbol) {
        String normalizedSymbol = normalizeSymbol(symbol);
        if (normalizedSymbol.isEmpty()) {
            return Collections.emptyList();
        }
        List<EarningsEventOutcome> rows = repository.findBySymbolOrderByEventDateDesc(normalizedSymbol);
        return rows == null ? Collections.emptyList() : rows;
    }

    @Override
    public EarningsEventOutcome getBySymbolAndPeriod(String symbol, String period) {
        String normalizedSymbol = normalizeSymbol(symbol);
        String normalizedPeriod = normalizePeriod(period);
        if (normalizedSymbol.isEmpty() || normalizedPeriod.isEmpty()) {
            return null;
        }
        return repository.findTopBySymbolAndNormalizedFiscalPeriodLabelOrderByEventDateDesc(
                normalizedSymbol,
                normalizedPeriod
        );
    }

    private String normalizeSymbol(String symbol) {
        return symbol == null ? "" : symbol.trim().toUpperCase();
    }

    private String normalizePeriod(String period) {
        if (period == null) {
            return "";
        }
        String normalized = period.trim().toUpperCase();
        if (normalized.startsWith("FY")) {
            normalized = normalized.substring(2);
        }
        return normalized;
    }
}
