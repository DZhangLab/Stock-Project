package com.summer.stockproject.dao;

import com.summer.stockproject.entity.IntradayBar;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IntradayBarRepository extends JpaRepository<IntradayBar, Integer> {
}
