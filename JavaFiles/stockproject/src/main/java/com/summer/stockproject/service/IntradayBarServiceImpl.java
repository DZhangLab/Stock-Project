package com.summer.stockproject.service;

import com.summer.stockproject.dao.IntradayBarRepository;
import com.summer.stockproject.entity.IntradayBar;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import javax.persistence.Query;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Date;
import java.util.List;

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
        // Validate table name contains only letters and numbers to prevent SQL injection
        if (!tablename.matches("^[A-Z0-9]+$")) {
            throw new IllegalArgumentException("Invalid table name: " + tablename);
        }

        // Handle META -> FB mapping (Facebook changed ticker from FB to META)
        if (tablename.equals("META")) {
            tablename = "FB";
        }

        String sql = "SELECT * FROM `" + tablename + "` u WHERE u.timePoint >= :start AND u.timePoint <= :end ORDER BY u.timePoint ASC";
        Query query = entityManager.createNativeQuery(sql, IntradayBar.class);
        query.setParameter("start", start);
        query.setParameter("end", end);

        @SuppressWarnings("unchecked")
        List<IntradayBar> result = query.getResultList();
        return result;
    }

    @Override
    public Timestamp getLatestTimePoint(String tablename) {
        // Validate table name contains only letters and numbers to prevent SQL injection
        if (!tablename.matches("^[A-Z0-9]+$")) {
            throw new IllegalArgumentException("Invalid table name: " + tablename);
        }

        // Handle META -> FB mapping (Facebook changed ticker from FB to META)
        if (tablename.equals("META")) {
            tablename = "FB";
        }

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
