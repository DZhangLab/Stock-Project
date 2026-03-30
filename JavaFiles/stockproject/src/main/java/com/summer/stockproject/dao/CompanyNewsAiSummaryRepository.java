package com.summer.stockproject.dao;

import com.summer.stockproject.entity.CompanyNewsAiSummary;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CompanyNewsAiSummaryRepository extends JpaRepository<CompanyNewsAiSummary, Long> {
    CompanyNewsAiSummary findTopBySymbolOrderByUpdatedAtDescAnalysisDateDesc(String symbol);
}
