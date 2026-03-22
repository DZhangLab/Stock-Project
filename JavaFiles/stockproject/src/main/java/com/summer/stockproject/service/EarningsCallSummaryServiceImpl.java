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
        return repository.findTopBySymbolOrderByUpdatedAtDescFiscalPeriodLabelDesc(normalized);
    }
}
