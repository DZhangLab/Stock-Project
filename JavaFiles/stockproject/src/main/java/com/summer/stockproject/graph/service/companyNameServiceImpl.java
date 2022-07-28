package com.summer.stockproject.graph.service;

import com.summer.stockproject.graph.dao.companyNameRepository;
import com.summer.stockproject.graph.entity.companyNames;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class companyNameServiceImpl implements companyNameService{

    private companyNameRepository companyNameRepository;

    @Autowired
    public companyNameServiceImpl(companyNameRepository companNameRepository) {
        this.companyNameRepository = companNameRepository;
    }

    @Override
    public List<companyNames> findAll() {
        return companyNameRepository.findAll();
    }

    @Override
    public companyNames findBycompanyName(String name) {
        return companyNameRepository.findBycompanyName(name);
    }
}
