package com.summer.stockproject.dao;

import com.summer.stockproject.entity.EarningsAiAnalysis;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EarningsAiAnalysisRepository extends JpaRepository<EarningsAiAnalysis, Long> {
    EarningsAiAnalysis findTopBySymbolOrderByUpdatedAtDescFiscalPeriodLabelDesc(String symbol);
}
