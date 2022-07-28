package com.summer.stockproject.graph.dao;

import com.summer.stockproject.graph.entity.companyNames;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface companyNameRepository extends JpaRepository<companyNames, String> {
    companyNames findBycompanyName(String name);
}
