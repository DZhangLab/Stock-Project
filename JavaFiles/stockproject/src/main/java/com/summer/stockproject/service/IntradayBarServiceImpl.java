package com.summer.stockproject.service;

import com.summer.stockproject.dao.IntradayBarRepository;
import com.summer.stockproject.entity.IntradayBar;
import com.summer.stockproject.util.SymbolNormalizer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import javax.persistence.Query;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class IntradayBarServiceImpl implements IntradayBarService {

    private final IntradayBarRepository intradayBarRepository;

    @PersistenceContext
    private EntityManager entityManager;

    @Autowired
    public IntradayBarServiceImpl(IntradayBarRepository intradayBarRepository) {
        this.intradayBarRepository = intradayBarRepository;
    }

    @Override
    public List<IntradayBar> findAll() {
        return intradayBarRepository.findAll();
    }

    @Override
    public IntradayBar getByTimePoint(LocalDateTime timepoint) {
        return intradayBarRepository.getByTimePoint(timepoint);
    }

    @Override
    public IntradayBar getById(int theid) {
        return intradayBarRepository.getById(theid);
    }

    @Override
    public List<IntradayBar> findByStartDateBetween(Timestamp start, Timestamp end) {
        return intradayBarRepository.findByStartDateBetween(start, end);
    }

    @Override
    public List<IntradayBar> findBySingleDate(Timestamp date) {
        return intradayBarRepository.findBySingleDate(date);
    }

    @Override
    public List<IntradayBar> universalfind(String tablename, Timestamp start, Timestamp end) {
        // Validate + normalize (rejects injection, rewrites FB -> META).
        tablename = SymbolNormalizer.normalizeTableName(tablename);

        String sql = "SELECT * FROM `" + tablename + "` u WHERE u.timePoint >= :start AND u.timePoint <= :end ORDER BY u.timePoint ASC";
        Query query = entityManager.createNativeQuery(sql, IntradayBar.class);
        query.setParameter("start", start);
        query.setParameter("end", end);

        @SuppressWarnings("unchecked")
        List<IntradayBar> result = query.getResultList();
        return result;
    }

    @Override
    public List<IntradayBar> findAggregated(String tablename, Timestamp start, Timestamp end,
                                            int intervalMinutes) {
        List<IntradayBar> minuteBars = universalfind(tablename, start, end);
        if (minuteBars.isEmpty()) {
            return minuteBars;
        }

        // Align windows to session start (09:30).
        // Minutes-since-session-open is floored to the interval boundary.
        // E.g. with interval=10: 09:30→09:30, 09:37→09:30, 09:40→09:40, ...
        final int SESSION_START_HOUR = 9;
        final int SESSION_START_MIN = 30;

        Map<Long, IntradayBar> buckets = new LinkedHashMap<>();

        for (IntradayBar bar : minuteBars) {
            LocalDateTime dt = bar.getTimePoint().toLocalDateTime();
            int totalMin = dt.getHour() * 60 + dt.getMinute();
            int sessionBase = SESSION_START_HOUR * 60 + SESSION_START_MIN;
            int elapsed = totalMin - sessionBase;
            if (elapsed < 0) elapsed = 0;
            int windowOffset = (elapsed / intervalMinutes) * intervalMinutes;
            int windowMin = sessionBase + windowOffset;
            LocalDateTime windowStart = dt.toLocalDate()
                    .atTime(windowMin / 60, windowMin % 60, 0);
            long key = Timestamp.valueOf(windowStart).getTime();

            IntradayBar agg = buckets.get(key);
            if (agg == null) {
                agg = new IntradayBar();
                agg.setTimePoint(Timestamp.valueOf(windowStart));
                agg.setMinuteOpen(bar.getMinuteOpen());
                agg.setMinuteHigh(bar.getMinuteHigh());
                agg.setMinuteLow(bar.getMinuteLow());
                agg.setMinuteClose(bar.getMinuteClose());
                agg.setMinuteVolume(bar.getMinuteVolume() != null ? bar.getMinuteVolume() : 0.0);
                buckets.put(key, agg);
            } else {
                if (bar.getMinuteHigh() != null && (agg.getMinuteHigh() == null
                        || bar.getMinuteHigh().compareTo(agg.getMinuteHigh()) > 0)) {
                    agg.setMinuteHigh(bar.getMinuteHigh());
                }
                if (bar.getMinuteLow() != null && (agg.getMinuteLow() == null
                        || bar.getMinuteLow().compareTo(agg.getMinuteLow()) < 0)) {
                    agg.setMinuteLow(bar.getMinuteLow());
                }
                agg.setMinuteClose(bar.getMinuteClose());
                double vol = (agg.getMinuteVolume() != null ? agg.getMinuteVolume() : 0.0)
                        + (bar.getMinuteVolume() != null ? bar.getMinuteVolume() : 0.0);
                agg.setMinuteVolume(vol);
            }
        }

        return new ArrayList<>(buckets.values());
    }

    @Override
    public Timestamp getLatestTimePoint(String tablename) {
        // Validate + normalize (rejects injection, rewrites FB -> META).
        tablename = SymbolNormalizer.normalizeTableName(tablename);

        String sql = "SELECT MAX(timePoint) FROM `" + tablename + "`";
        Query query = entityManager.createNativeQuery(sql);
        Object result = query.getSingleResult();
        if (result == null) {
            return null;
        }
        if (result instanceof Timestamp) {
            return (Timestamp) result;
        }
        if (result instanceof Date) {
            return new Timestamp(((Date) result).getTime());
        }
        return null;
    }
}
