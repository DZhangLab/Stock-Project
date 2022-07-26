package com.summer.stockproject.graph.service;

import com.summer.stockproject.graph.entity.AAPL;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

public interface AAPLService {
    public List<AAPL> findAll();
    public AAPL getByTimePoint(LocalDateTime timepoint);

    public AAPL getById(int theid);

    List<AAPL> findByStartDateBetween(Timestamp start, Timestamp end);

    List<AAPL> findBySingleDate(Timestamp date);

    List<AAPL> universalfind(String tablename, Timestamp date);
}
