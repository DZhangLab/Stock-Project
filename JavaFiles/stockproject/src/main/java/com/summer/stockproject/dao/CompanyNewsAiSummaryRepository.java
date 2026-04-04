package com.summer.stockproject.dao;

import com.summer.stockproject.entity.CompanyNewsAiSummary;
import org.springframework.data.jpa.repository.JpaRepository;

import java.sql.Date;

public interface CompanyNewsAiSummaryRepository extends JpaRepository<CompanyNewsAiSummary, Long> {
    CompanyNewsAiSummary findTopBySymbolOrderByUpdatedAtDescAnalysisDateDesc(String symbol);

    /**
     * Exact calendar-day match: find a summary whose analysis_date equals
     * the given date.  Returns null when no summary exists for that day.
     */
    CompanyNewsAiSummary findTopBySymbolAndAnalysisDate(String symbol, Date analysisDate);

    /**
     * Fallback: find the most recent AI summary whose analysis_date < targetDate.
     * Used when no exact-day summary exists for the requested calendar day.
     */
    CompanyNewsAiSummary findTopBySymbolAndAnalysisDateLessThanOrderByAnalysisDateDesc(
            String symbol, Date targetDate);
}
