package com.summer.stockproject.service;

import com.summer.stockproject.entity.AAPL;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Date;
import java.util.List;

public interface AAPLService {
    public List<AAPL> findAll();
    public AAPL getByTimePoint(LocalDateTime timepoint);

    public AAPL getById(int theid);

    List<AAPL> findByStartDateBetween(Timestamp start, Timestamp end);
}
