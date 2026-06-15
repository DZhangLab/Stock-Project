package com.summer.stockproject.dao;

import com.summer.stockproject.entity.EarningsEventOutcome;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface EarningsEventOutcomeRepository extends JpaRepository<EarningsEventOutcome, Long> {

    List<EarningsEventOutcome> findBySymbolOrderByEventDateDesc(String symbol);

    EarningsEventOutcome findTopBySymbolAndNormalizedFiscalPeriodLabelOrderByEventDateDesc(
            String symbol,
            String normalizedFiscalPeriodLabel
    );

    @Query(
            value = "SELECT normalized_fiscal_period_label AS normalizedFiscalPeriodLabel, "
                    + "COALESCE(avg_pos_minus_neg_score, avg_positive_score - avg_negative_score) "
                    + "AS aiToneIndex "
                    + "FROM earnings_sentiment_features "
                    + "WHERE symbol = :symbol",
            nativeQuery = true
    )
    List<EarningsToneIndexProjection> findToneIndexesBySymbol(@Param("symbol") String symbol);
}
