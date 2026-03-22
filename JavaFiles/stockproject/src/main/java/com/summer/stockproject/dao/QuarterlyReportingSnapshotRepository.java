package com.summer.stockproject.dao;

import com.summer.stockproject.entity.QuarterlyReportingSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuarterlyReportingSnapshotRepository extends JpaRepository<QuarterlyReportingSnapshot, Long> {
    QuarterlyReportingSnapshot findTopBySymbolOrderByFiscalDateEndingDescUpdatedAtDesc(String symbol);
}
