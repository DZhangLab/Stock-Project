package com.summer.stockproject.service;

import com.summer.stockproject.entity.QuarterlyReportingSnapshot;

import java.util.List;
import java.util.Map;

public interface QuarterlyReportingSnapshotService {
    QuarterlyReportingSnapshot getLatestBySymbol(String symbol);

    List<Map<String, Object>> getRecentWithYoy(String symbol, int displayCount);
}
