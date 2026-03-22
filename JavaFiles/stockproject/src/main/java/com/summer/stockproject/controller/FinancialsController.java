package com.summer.stockproject.controller;

import com.summer.stockproject.entity.QuarterlyReportingSnapshot;
import com.summer.stockproject.service.QuarterlyReportingSnapshotService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/financials")
public class FinancialsController {

    private final QuarterlyReportingSnapshotService quarterlyReportingSnapshotService;

    @Autowired
    public FinancialsController(QuarterlyReportingSnapshotService quarterlyReportingSnapshotService) {
        this.quarterlyReportingSnapshotService = quarterlyReportingSnapshotService;
    }

    @GetMapping("/quarterly/latest")
    public ResponseEntity<Map<String, Object>> getLatestQuarterlySnapshot(
            @RequestParam(defaultValue = "AAPL") String symbol
    ) {
        QuarterlyReportingSnapshot snapshot = quarterlyReportingSnapshotService.getLatestBySymbol(symbol);
        if (snapshot == null) {
            Map<String, Object> notFound = new LinkedHashMap<String, Object>();
            notFound.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
            notFound.put("message", "No quarterly snapshot found");
            return ResponseEntity.status(404).body(notFound);
        }

        Map<String, Object> response = new LinkedHashMap<String, Object>();
        response.put("symbol", snapshot.getSymbol());
        response.put("fiscalDateEnding", snapshot.getFiscalDateEnding() == null ? null : snapshot.getFiscalDateEnding().toString());
        response.put("fiscalPeriodLabel", snapshot.getFiscalPeriodLabel());
        response.put("reportedDate", snapshot.getReportedDate() == null ? null : snapshot.getReportedDate().toString());
        response.put("reportedCurrency", snapshot.getReportedCurrency());
        response.put("totalRevenue", snapshot.getTotalRevenue());
        response.put("netIncome", snapshot.getNetIncome());
        response.put("reportedEps", snapshot.getReportedEps());
        response.put("estimatedEps", snapshot.getEstimatedEps());
        response.put("surprise", snapshot.getSurprise());
        response.put("surprisePercentage", snapshot.getSurprisePercentage());
        response.put("updatedAt", snapshot.getUpdatedAt() == null ? null : snapshot.getUpdatedAt().toString());
        return ResponseEntity.ok(response);
    }
}
