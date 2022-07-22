package com.summer.stockproject.dao;

import com.summer.stockproject.entity.mykey;
import com.summer.stockproject.entity.timestamptable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface timestampRepository extends JpaRepository<timestamptable, mykey> {
    List<timestamptable> findAll();
}
