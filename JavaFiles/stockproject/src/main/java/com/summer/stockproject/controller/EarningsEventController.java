package com.summer.stockproject.controller;

import com.summer.stockproject.entity.EarningsEventOutcome;
import com.summer.stockproject.service.EarningsEventOutcomeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/earnings-events")
public class EarningsEventController {

    private final EarningsEventOutcomeService service;

    @Autowired
    public EarningsEventController(EarningsEventOutcomeService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<Map<String, Object>> getBySymbol(
            @RequestParam(defaultValue = "AAPL") String symbol
    ) {
        List<EarningsEventOutcome> rows = service.getBySymbol(symbol);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", normalizeSymbol(symbol));
        response.put("count", rows.size());

        List<Map<String, Object>> events = new ArrayList<>(rows.size());
        for (EarningsEventOutcome row : rows) {
            events.add(buildResponse(row));
        }
        response.put("events", events);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/aggregate")
    public ResponseEntity<Map<String, Object>> getAggregate(
            @RequestParam(defaultValue = "tone") String bucket,
            @RequestParam(defaultValue = "5d") String window,
            @RequestParam(required = false) String symbol,
            @RequestParam(required = false) String symbols,
            @RequestParam(required = false) String quality,
            @RequestParam(defaultValue = "5") int minBucketSize,
            @RequestParam(defaultValue = "1000") int bootstrapSamples
    ) {
        try {
            return ResponseEntity.ok(service.getAggregateAnalysis(
                    bucket,
                    window,
                    symbol,
                    symbols,
                    quality,
                    minBucketSize,
                    bootstrapSamples
            ));
        } catch (IllegalArgumentException ex) {
            Map<String, Object> badRequest = new LinkedHashMap<>();
            badRequest.put("message", ex.getMessage());
            return ResponseEntity.badRequest().body(badRequest);
        }
    }

    @GetMapping("/{symbol}/{period}")
    public ResponseEntity<Map<String, Object>> getBySymbolAndPeriod(
            @PathVariable String symbol,
            @PathVariable String period
    ) {
        EarningsEventOutcome row = service.getBySymbolAndPeriod(symbol, period);
        if (row == null) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", normalizeSymbol(symbol));
            notFound.put("period", period == null ? "" : period.trim().toUpperCase());
            notFound.put("message", "No earnings event outcome found");
            return ResponseEntity.status(404).body(notFound);
        }
        return ResponseEntity.ok(buildResponse(row));
    }

    private Map<String, Object> buildResponse(EarningsEventOutcome row) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", row.getSymbol());
        response.put("fiscalPeriodLabel", row.getFiscalPeriodLabel());
        response.put("normalizedFiscalPeriodLabel", row.getNormalizedFiscalPeriodLabel());
        response.put("eventDate", row.getEventDate() == null ? null : row.getEventDate().toString());
        response.put("eventDateBasis", row.getEventDateBasis());
        response.put("eventReleaseTime", row.getEventReleaseTime());
        response.put("firstReactionDate", row.getFirstReactionDate() == null ? null : row.getFirstReactionDate().toString());
        response.put("preEventClose", row.getPreEventClose());
        response.put("ret1d", row.getRet1d());
        response.put("ret3d", row.getRet3d());
        response.put("ret5d", row.getRet5d());
        response.put("ret20d", row.getRet20d());
        response.put("car3d", row.getCar3d());
        response.put("car5d", row.getCar5d());
        response.put("car20d", row.getCar20d());
        response.put("surprisePctAtEvent", row.getSurprisePctAtEvent());
        response.put("aiOverallToneAtEvent", row.getAiOverallToneAtEvent());
        response.put("aiToneIndex", row.getAiToneIndex());
        response.put("qualityFlag", row.getQualityFlag());
        response.put("exclusionReason", row.getExclusionReason());
        response.put("computedAt", row.getComputedAt() == null ? null : row.getComputedAt().toString());
        return response;
    }

    private String normalizeSymbol(String symbol) {
        return symbol == null ? "" : symbol.trim().toUpperCase();
    }
}
