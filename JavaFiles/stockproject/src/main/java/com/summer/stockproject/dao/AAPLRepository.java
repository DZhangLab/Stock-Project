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
    @Query("select u from AAPL u where u.timePoint >= ?1 and u.timePoint <= ?2")
    List<AAPL> findByStartDateBetween(Timestamp start, Timestamp end);

    @Query("select u from AAPL u where u.timePoint = ?1 ")
    List<AAPL> findBySingleDate(Timestamp date);

    // Note: JPA does not support table name as parameter, need to use EntityManager in Service layer to dynamically build query
    // This method is kept for compatibility, actual implementation is in Service layer
    @Query(value="SELECT * FROM AAPL u where u.timePoint >= ?1 and u.timePoint <= ?2", nativeQuery = true)
    List<AAPL> findByDateRange(Timestamp start, Timestamp end);
}
