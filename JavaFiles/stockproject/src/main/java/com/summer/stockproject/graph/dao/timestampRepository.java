package com.summer.stockproject.graph.dao;

import com.summer.stockproject.graph.entity.mykey;
import com.summer.stockproject.graph.entity.timestamptable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.sql.Timestamp;
import java.util.List;

public interface timestampRepository extends JpaRepository<timestamptable, mykey> {
    List<timestamptable> findAll();
    @Query("select u from timestamptable u where u.mykey.timePoint > ?1 and u.mykey.timePoint < ?2")
    List<timestamptable> findByStartDateBetween(Timestamp start, Timestamp end);
}
