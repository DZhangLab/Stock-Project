package com.summer.stockproject.dao;

import com.summer.stockproject.entity.AAPL;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Date;
import java.util.List;

public interface AAPLRepository extends JpaRepository<AAPL, Integer> {

    AAPL getByTimePoint(LocalDateTime timepoint);
    //public List<AAPL> findFirst10();
    @Query("select u from AAPL u where u.timePoint > ?1 and u.timePoint < ?2")
    List<AAPL> findByStartDateBetween(Timestamp start, Timestamp end);


}
