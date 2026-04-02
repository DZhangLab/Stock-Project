package com.summer.stockproject.dao;

import com.summer.stockproject.entity.QuarterlyReportingSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface QuarterlyReportingSnapshotRepository extends JpaRepository<QuarterlyReportingSnapshot, Long> {
    QuarterlyReportingSnapshot findTopBySymbolOrderByFiscalDateEndingDescUpdatedAtDesc(String symbol);

    List<QuarterlyReportingSnapshot> findTop8BySymbolOrderByFiscalDateEndingDesc(String symbol);
}
