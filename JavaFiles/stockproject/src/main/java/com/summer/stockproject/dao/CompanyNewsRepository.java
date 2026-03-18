package com.summer.stockproject.dao;

import com.summer.stockproject.entity.CompanyNews;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CompanyNewsRepository extends JpaRepository<CompanyNews, Long> {
    List<CompanyNews> findTop20BySymbolOrderByPublishedAtDesc(String symbol);
}
