package com.summer.stockproject.service;

import com.summer.stockproject.dao.CompanyNewsRepository;
import com.summer.stockproject.entity.CompanyNews;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.Collections;
import java.util.List;

@Service
public class CompanyNewsServiceImpl implements CompanyNewsService {

    private final CompanyNewsRepository companyNewsRepository;

    @Autowired
    public CompanyNewsServiceImpl(CompanyNewsRepository companyNewsRepository) {
        this.companyNewsRepository = companyNewsRepository;
    }

    @Override
    public List<CompanyNews> getRecentNews(String symbol) {
        return companyNewsRepository.findTop20BySymbolOrderByPublishedAtDesc(
                symbol != null ? symbol.trim().toUpperCase() : "AAPL");
    }

    @Override
    public List<CompanyNews> getNewsBySymbolAndDateRange(String symbol,
                                                          String rangeStart,
                                                          String rangeEnd) {
        if (symbol == null || rangeStart == null || rangeEnd == null) {
            return Collections.emptyList();
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return Collections.emptyList();
        }

        // Calendar-day rule (all times ET, matching the rest of the stock page):
        //   from = rangeStart 00:00:00
        //   to   = (rangeEnd + 1 day) 00:00:00  (exclusive upper bound)
        //
        // Spring Data "Between" is inclusive on both sides, so we subtract
        // one second from the upper bound to keep the window within rangeEnd.
        //   from = rangeStart  00:00:00.000
        //   to   = rangeEnd    23:59:59.000
        LocalDate startDate = LocalDate.parse(rangeStart);
        LocalDate endDate = LocalDate.parse(rangeEnd);

        Timestamp from = Timestamp.valueOf(startDate.atTime(LocalTime.MIDNIGHT));
        Timestamp to = Timestamp.valueOf(endDate.atTime(LocalTime.of(23, 59, 59)));

        return companyNewsRepository
                .findTop20BySymbolAndPublishedAtBetweenOrderByPublishedAtDesc(
                        normalized, from, to);
    }
}
