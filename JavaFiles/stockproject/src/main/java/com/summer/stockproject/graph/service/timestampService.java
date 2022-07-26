package com.summer.stockproject.graph.service;

import com.summer.stockproject.graph.entity.timestamptable;

import java.sql.Timestamp;
import java.util.List;

public interface timestampService {
    List<timestamptable> findAll();

    List<timestamptable> findByStartDateBetween(Timestamp start, Timestamp end);
}
