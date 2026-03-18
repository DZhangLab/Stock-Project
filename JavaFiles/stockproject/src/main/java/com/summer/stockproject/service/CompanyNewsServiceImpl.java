package com.summer.stockproject.service;

import com.summer.stockproject.dao.CompanyNewsRepository;
import com.summer.stockproject.entity.CompanyNews;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CompanyNewsServiceImpl implements CompanyNewsService {

    private final CompanyNewsRepository companyNewsRepository;

    @Autowired
    public CompanyNewsServiceImpl(CompanyNewsRepository companyNewsRepository) {
        this.companyNewsRepository = companyNewsRepository;
    }

    @Override
    public List<CompanyNews> getRecentAppleNews() {
        return companyNewsRepository.findTop20BySymbolOrderByPublishedAtDesc("AAPL");
    }
}
