package com.summer.stockproject.dao;

import com.summer.stockproject.entity.DailyQuote;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DailyQuoteRepository extends JpaRepository<DailyQuote, Integer> {
}
