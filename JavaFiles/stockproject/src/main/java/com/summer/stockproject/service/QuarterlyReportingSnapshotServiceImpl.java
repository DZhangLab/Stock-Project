package com.summer.stockproject.service;

import com.summer.stockproject.dao.QuarterlyReportingSnapshotRepository;
import com.summer.stockproject.entity.QuarterlyReportingSnapshot;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class QuarterlyReportingSnapshotServiceImpl implements QuarterlyReportingSnapshotService {

    private final QuarterlyReportingSnapshotRepository repository;

    private static final Pattern PERIOD_PATTERN = Pattern.compile("FY(\\d{4})Q([1-4])");

    @Autowired
    public QuarterlyReportingSnapshotServiceImpl(QuarterlyReportingSnapshotRepository repository) {
        this.repository = repository;
    }

    @Override
    public QuarterlyReportingSnapshot getLatestBySymbol(String symbol) {
        if (symbol == null) {
            return null;
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return null;
        }
        return repository.findTopBySymbolOrderByFiscalDateEndingDescUpdatedAtDesc(normalized);
    }

    @Override
    public List<Map<String, Object>> getRecentWithYoy(String symbol, int displayCount) {
        if (symbol == null) {
            return Collections.emptyList();
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return Collections.emptyList();
        }

        List<QuarterlyReportingSnapshot> all = repository.findTop8BySymbolOrderByFiscalDateEndingDesc(normalized);
        if (all == null || all.isEmpty()) {
            return Collections.emptyList();
        }

        // Build lookup: "FY2025Q3" -> snapshot
        Map<String, QuarterlyReportingSnapshot> byPeriod = new HashMap<>();
        for (QuarterlyReportingSnapshot s : all) {
            if (s.getFiscalPeriodLabel() != null) {
                byPeriod.put(s.getFiscalPeriodLabel(), s);
            }
        }

        List<QuarterlyReportingSnapshot> display = all.subList(0, Math.min(displayCount, all.size()));
        List<Map<String, Object>> result = new ArrayList<>();

        for (QuarterlyReportingSnapshot current : display) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("symbol", current.getSymbol());
            row.put("fiscalDateEnding", current.getFiscalDateEnding() == null ? null : current.getFiscalDateEnding().toString());
            row.put("fiscalPeriodLabel", current.getFiscalPeriodLabel());
            row.put("reportedDate", current.getReportedDate() == null ? null : current.getReportedDate().toString());
            row.put("reportedCurrency", current.getReportedCurrency());
            row.put("totalRevenue", current.getTotalRevenue());
            row.put("grossProfit", current.getGrossProfit());
            row.put("operatingIncome", current.getOperatingIncome());
            row.put("netIncome", current.getNetIncome());
            row.put("reportedEps", current.getReportedEps());
            row.put("estimatedEps", current.getEstimatedEps());
            row.put("surprise", current.getSurprise());
            row.put("surprisePercentage", current.getSurprisePercentage());

            // Find year-ago quarter for YoY
            String yoyPeriod = yearAgoPeriod(current.getFiscalPeriodLabel());
            QuarterlyReportingSnapshot yearAgo = yoyPeriod != null ? byPeriod.get(yoyPeriod) : null;

            row.put("totalRevenueYoyPct", computeYoyPct(current.getTotalRevenue(), yearAgo != null ? yearAgo.getTotalRevenue() : null));
            row.put("netIncomeYoyPct", computeYoyPct(current.getNetIncome(), yearAgo != null ? yearAgo.getNetIncome() : null));
            row.put("reportedEpsYoyPct", computeYoyPct(current.getReportedEps(), yearAgo != null ? yearAgo.getReportedEps() : null));

            result.add(row);
        }

        return result;
    }

    private static String yearAgoPeriod(String periodLabel) {
        if (periodLabel == null) {
            return null;
        }
        Matcher m = PERIOD_PATTERN.matcher(periodLabel);
        if (!m.matches()) {
            return null;
        }
        int year = Integer.parseInt(m.group(1));
        String quarter = m.group(2);
        return "FY" + (year - 1) + "Q" + quarter;
    }

    private static BigDecimal computeYoyPct(BigDecimal current, BigDecimal yearAgo) {
        if (current == null || yearAgo == null || yearAgo.compareTo(BigDecimal.ZERO) == 0) {
            return null;
        }
        return current.subtract(yearAgo)
                .multiply(BigDecimal.valueOf(100))
                .divide(yearAgo.abs(), 2, RoundingMode.HALF_UP);
    }
}
