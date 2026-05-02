package com.summer.stockproject.service;

import com.summer.stockproject.dao.DailyVolatilityRepository;
import com.summer.stockproject.entity.DailyVolatility;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
public class DailyVolatilityServiceImpl implements DailyVolatilityService {

    /** Hard upper bound on history rows returned by /history. */
    private static final int MAX_HISTORY_DAYS = 5000;

    /** Lower bound (defensive — callers should not pass <= 0). */
    private static final int MIN_HISTORY_DAYS = 1;

    private final DailyVolatilityRepository repository;

    @Autowired
    public DailyVolatilityServiceImpl(DailyVolatilityRepository repository) {
        this.repository = repository;
    }

    @Override
    public DailyVolatility getLatestBySymbol(String symbol) {
        if (symbol == null) {
            return null;
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return null;
        }
        return repository.findTopBySymbolOrderByAsOfDateDesc(normalized);
    }

    @Override
    public List<DailyVolatility> getRecentBySymbol(String symbol, int days) {
        if (symbol == null) {
            return Collections.emptyList();
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return Collections.emptyList();
        }
        int boundedDays = Math.max(MIN_HISTORY_DAYS, Math.min(days, MAX_HISTORY_DAYS));
        List<DailyVolatility> desc = repository.findBySymbolOrderByAsOfDateDesc(
                normalized, PageRequest.of(0, boundedDays));
        if (desc == null || desc.isEmpty()) {
            return Collections.emptyList();
        }
        // Reverse to ascending order so consumers can render directly without sorting.
        List<DailyVolatility> asc = new ArrayList<>(desc);
        Collections.reverse(asc);
        return asc;
    }
}
