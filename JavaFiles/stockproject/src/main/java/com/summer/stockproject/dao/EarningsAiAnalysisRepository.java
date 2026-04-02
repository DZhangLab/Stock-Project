package com.summer.stockproject.dao;

import com.summer.stockproject.entity.EarningsAiAnalysis;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface EarningsAiAnalysisRepository extends JpaRepository<EarningsAiAnalysis, Long> {
    EarningsAiAnalysis findTopBySymbolOrderByFiscalPeriodLabelDesc(String symbol);

    @Query("SELECT DISTINCT e.fiscalPeriodLabel FROM EarningsAiAnalysis e WHERE e.symbol = ?1 ORDER BY e.fiscalPeriodLabel DESC")
    List<String> findPeriodsBySymbol(String symbol);

    EarningsAiAnalysis findBySymbolAndFiscalPeriodLabel(String symbol, String fiscalPeriodLabel);
}
