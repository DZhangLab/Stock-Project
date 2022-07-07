package com.summer.stockproject.dao;

import com.summer.stockproject.entity.AAPL;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;

public interface AAPLRepository extends JpaRepository<AAPL, Integer> {

    public AAPL getByTimePoint(LocalDateTime timepoint);
}
