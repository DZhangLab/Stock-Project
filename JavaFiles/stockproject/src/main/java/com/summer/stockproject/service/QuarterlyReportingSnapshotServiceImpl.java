package com.summer.stockproject.service;

import com.summer.stockproject.dao.QuarterlyReportingSnapshotRepository;
import com.summer.stockproject.entity.QuarterlyReportingSnapshot;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class QuarterlyReportingSnapshotServiceImpl implements QuarterlyReportingSnapshotService {

    private final QuarterlyReportingSnapshotRepository repository;

    @Autowired
    public QuarterlyReportingSnapshotServiceImpl(QuarterlyReportingSnapshotRepository repository) {
        this.repository = repository;
    }

    @Override
    public QuarterlyReportingSnapshot getLatestBySymbol(String symbol) {
        if (symbol == null) {
            return null;
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return null;
        }
        return repository.findTopBySymbolOrderByFiscalDateEndingDescUpdatedAtDesc(normalized);
    }
}
