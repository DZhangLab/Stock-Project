package com.summer.stockproject.graph.service;

import com.summer.stockproject.graph.dao.timestampRepository;
import com.summer.stockproject.graph.entity.timestamptable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.util.List;
@Service
public class timestampServiceImpl implements timestampService{
    public timestampRepository timestampRepository;

    @Autowired
    public timestampServiceImpl(timestampRepository timestampRepository) {
        this.timestampRepository = timestampRepository;
    }
    @Override
    public List<timestamptable> findAll() {
        return timestampRepository.findAll();
    }

    @Override
    public List<timestamptable> findByStartDateBetween(Timestamp start, Timestamp end) {
        return timestampRepository.findByStartDateBetween(start, end);
    }
}
