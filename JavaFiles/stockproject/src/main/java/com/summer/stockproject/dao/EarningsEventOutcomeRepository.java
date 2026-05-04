package com.summer.stockproject.dao;

import com.summer.stockproject.entity.EarningsEventOutcome;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface EarningsEventOutcomeRepository extends JpaRepository<EarningsEventOutcome, Long> {

    List<EarningsEventOutcome> findBySymbolOrderByEventDateDesc(String symbol);

    EarningsEventOutcome findTopBySymbolAndNormalizedFiscalPeriodLabelOrderByEventDateDesc(
            String symbol,
            String normalizedFiscalPeriodLabel
    );
}
