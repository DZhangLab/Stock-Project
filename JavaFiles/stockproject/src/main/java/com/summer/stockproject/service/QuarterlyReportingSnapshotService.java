package com.summer.stockproject.service;

import com.summer.stockproject.entity.QuarterlyReportingSnapshot;

public interface QuarterlyReportingSnapshotService {
    QuarterlyReportingSnapshot getLatestBySymbol(String symbol);
}
