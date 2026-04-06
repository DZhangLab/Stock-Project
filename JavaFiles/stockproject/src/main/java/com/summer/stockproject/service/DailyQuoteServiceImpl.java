package com.summer.stockproject.service;

import com.summer.stockproject.entity.DailyQuote;
import org.springframework.stereotype.Service;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import javax.persistence.Query;
import java.util.List;

@Service
public class DailyQuoteServiceImpl implements DailyQuoteService {

    @PersistenceContext
    private EntityManager entityManager;

    private String normalizeSymbol(String symbol) {
        if ("FB".equalsIgnoreCase(symbol)) {
            return "META";
        }
        return symbol;
    }

    @Override
    public List<DailyQuote> findBySymbolAndDateRange(String symbol, String startDate, String endDate) {
        String normalized = normalizeSymbol(symbol);

        String sql = "SELECT * FROM everydayAfterClose " +
                "WHERE symbol = :symbol AND datetime >= :startDate AND datetime <= :endDate " +
                "ORDER BY datetime ASC";
        Query query = entityManager.createNativeQuery(sql, DailyQuote.class);
        query.setParameter("symbol", normalized);
        query.setParameter("startDate", startDate);
        query.setParameter("endDate", endDate);

        @SuppressWarnings("unchecked")
        List<DailyQuote> result = query.getResultList();
        return result;
    }

    @Override
    public String getLatestDateForSymbol(String symbol) {
        String normalized = normalizeSymbol(symbol);

        String sql = "SELECT MAX(datetime) FROM everydayAfterClose WHERE symbol = :symbol";
        Query query = entityManager.createNativeQuery(sql);
        query.setParameter("symbol", normalized);

        Object result = query.getSingleResult();
        return result != null ? result.toString() : null;
    }
}
