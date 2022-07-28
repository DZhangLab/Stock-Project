package com.summer.stockproject.graph.service;

import com.summer.stockproject.graph.entity.companyNames;
import org.springframework.stereotype.Service;

import java.util.List;

public interface companyNameService {
    public List<companyNames> findAll();
    public     companyNames findBycompanyName(String name);
}
