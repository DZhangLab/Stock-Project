package com.summer.stockproject.dao;

import com.summer.stockproject.entity.EarningsAiAnalysis;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface EarningsAiAnalysisRepository extends JpaRepository<EarningsAiAnalysis, Long> {
    @Query(
            value = "SELECT id FROM earnings_ai_analysis WHERE symbol = ?1 ORDER BY updated_at DESC, id DESC LIMIT 1",
            nativeQuery = true
    )
    Long findLatestIdBySymbol(String symbol);
}
