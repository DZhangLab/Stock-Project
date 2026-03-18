package com.summer.stockproject.dao;

import com.summer.stockproject.entity.IntradayBar;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

public interface IntradayBarRepository extends JpaRepository<IntradayBar, Integer> {

    IntradayBar getByTimePoint(LocalDateTime timepoint);

    @Query("select u from IntradayBar u where u.timePoint >= ?1 and u.timePoint <= ?2")
    List<IntradayBar> findByStartDateBetween(Timestamp start, Timestamp end);

    @Query("select u from IntradayBar u where u.timePoint = ?1 ")
    List<IntradayBar> findBySingleDate(Timestamp date);

    // Note: JPA does not support table name as parameter, need to use EntityManager in Service layer to dynamically build query
    // This method is kept for compatibility, actual implementation is in Service layer
    @Query(value="SELECT * FROM AAPL u where u.timePoint >= ?1 and u.timePoint <= ?2", nativeQuery = true)
    List<IntradayBar> findByDateRange(Timestamp start, Timestamp end);
}
