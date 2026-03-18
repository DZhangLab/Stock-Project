package com.summer.stockproject.service;

import com.summer.stockproject.entity.IntradayBar;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

public interface IntradayBarService {
    List<IntradayBar> findAll();

    IntradayBar getByTimePoint(LocalDateTime timepoint);

    IntradayBar getById(int theid);

    List<IntradayBar> findByStartDateBetween(Timestamp start, Timestamp end);

    List<IntradayBar> findBySingleDate(Timestamp date);

    List<IntradayBar> universalfind(String tablename, Timestamp start, Timestamp end);

    Timestamp getLatestTimePoint(String tablename);
}
