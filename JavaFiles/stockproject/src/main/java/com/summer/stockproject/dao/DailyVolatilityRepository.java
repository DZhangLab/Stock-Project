package com.summer.stockproject.dao;

import com.summer.stockproject.entity.DailyVolatility;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DailyVolatilityRepository extends JpaRepository<DailyVolatility, Long> {

    /**
     * Most recent daily_volatility row for a symbol.
     * Uses the descending (symbol, as_of_date DESC) index.
     */
    DailyVolatility findTopBySymbolOrderByAsOfDateDesc(String symbol);

    /**
     * Recent rows for a symbol in descending date order.  Callers pass
     * a Pageable with the desired row count (e.g. PageRequest.of(0, 180))
     * and reorder client-side as needed.  Uses the descending index.
     */
    List<DailyVolatility> findBySymbolOrderByAsOfDateDesc(String symbol, Pageable pageable);
}
