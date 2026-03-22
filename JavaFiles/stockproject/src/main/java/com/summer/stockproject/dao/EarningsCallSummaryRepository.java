package com.summer.stockproject.dao;

import com.summer.stockproject.entity.EarningsCallSummary;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EarningsCallSummaryRepository extends JpaRepository<EarningsCallSummary, Long> {
    EarningsCallSummary findTopBySymbolOrderByUpdatedAtDescFiscalPeriodLabelDesc(String symbol);
}
