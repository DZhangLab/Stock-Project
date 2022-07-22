package com.summer.stockproject.service;

import com.summer.stockproject.dao.timestampRepository;
import com.summer.stockproject.entity.timestamptable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

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
}
