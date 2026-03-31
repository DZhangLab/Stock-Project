package com.summer.stockproject.service;

import com.summer.stockproject.dao.EarningsAiAnalysisRepository;
import com.summer.stockproject.entity.EarningsAiAnalysis;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

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
        return repository.findTopBySymbolOrderByUpdatedAtDescFiscalPeriodLabelDesc(normalized);
    }
}
