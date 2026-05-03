package com.summer.stockproject.controller;

import com.summer.stockproject.entity.DailyVolatility;
import com.summer.stockproject.service.DailyVolatilityService;
import com.summer.stockproject.service.VolatilityModelEvaluationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import com.summer.stockproject.entity.VolatilityModelEvaluation;

/**
 * REST endpoints for the Phase 2 Daily Volatility MVP.
 *
 * Phase scope:
 *   - /latest and /history return realized vol, regime, and the
 *     descriptive ±1-sigma close envelope plus the empirical
 *     trailing-90d hit rate.
 *   - HAR-RV columns are exposed as nullable fields only — they
 *     are populated by Phase 3 and remain null in this phase.
 *     Frontend code must not present them as active forecasts.
 *
 * /regime endpoint is intentionally not provided.  The current
 * regime is fully captured by /latest.volatilityRegime, so a
 * separate endpoint would only duplicate that value.
 */
@RestController
@RequestMapping("/api/volatility")
public class VolatilityController {

    private final DailyVolatilityService service;
    private final VolatilityModelEvaluationService evaluationService;

    @Autowired
    public VolatilityController(
            DailyVolatilityService service,
            VolatilityModelEvaluationService evaluationService
    ) {
        this.service = service;
        this.evaluationService = evaluationService;
    }

    @GetMapping("/latest")
    public ResponseEntity<Map<String, Object>> getLatest(
            @RequestParam(defaultValue = "AAPL") String symbol) {
        DailyVolatility row = service.getLatestBySymbol(symbol);
        if (row == null) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
            notFound.put("message", "No daily volatility row found");
            return ResponseEntity.status(404).body(notFound);
        }
        return ResponseEntity.ok(buildLatestResponse(row));
    }

    @GetMapping("/history")
    public ResponseEntity<Map<String, Object>> getHistory(
            @RequestParam(defaultValue = "AAPL") String symbol,
            @RequestParam(defaultValue = "180") int days) {

        List<DailyVolatility> rows = service.getRecentBySymbol(symbol, days);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
        response.put("days", days);
        response.put("count", rows.size());

        List<Map<String, Object>> series = new ArrayList<>(rows.size());
        for (DailyVolatility r : rows) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("asOfDate", r.getAsOfDate() == null ? null : r.getAsOfDate().toString());
            item.put("realizedVol21d", r.getRealizedVol21d());
            item.put("volBandLow", r.getVolBandLow());
            item.put("volBandHigh", r.getVolBandHigh());
            item.put("volatilityRegime", r.getVolatilityRegime());
            series.add(item);
        }
        response.put("series", series);

        return ResponseEntity.ok(response);
    }

    @GetMapping("/evaluation/latest")
    public ResponseEntity<Map<String, Object>> getLatestEvaluation(
            @RequestParam(defaultValue = "AAPL") String symbol) {
        List<VolatilityModelEvaluation> rows = evaluationService.getLatestBySymbol(symbol);
        if (rows.isEmpty()) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
            notFound.put("message", "No volatility model evaluation rows found");
            return ResponseEntity.status(404).body(notFound);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", symbol == null ? "" : symbol.trim().toUpperCase());
        response.put("count", rows.size());

        List<Map<String, Object>> evaluations = new ArrayList<>(rows.size());
        for (VolatilityModelEvaluation row : rows) {
            evaluations.add(buildEvaluationResponse(row));
        }
        response.put("evaluations", evaluations);
        return ResponseEntity.ok(response);
    }

    private Map<String, Object> buildEvaluationResponse(VolatilityModelEvaluation row) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("modelName", row.getModelName());
        response.put("evalWindowStart", row.getEvalWindowStart() == null ? null : row.getEvalWindowStart().toString());
        response.put("evalWindowEnd", row.getEvalWindowEnd() == null ? null : row.getEvalWindowEnd().toString());
        response.put("evalWindowDays", row.getEvalWindowDays());
        response.put("mae", row.getMae());
        response.put("rmse", row.getRmse());
        response.put("qlike", row.getQlike());
        response.put("nObservations", row.getNObservations());
        response.put("computedAt", row.getComputedAt() == null ? null : row.getComputedAt().toString());
        return response;
    }

    private Map<String, Object> buildLatestResponse(DailyVolatility row) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", row.getSymbol());
        response.put("asOfDate", row.getAsOfDate() == null ? null : row.getAsOfDate().toString());
        response.put("realizedVol5d", row.getRealizedVol5d());
        response.put("realizedVol21d", row.getRealizedVol21d());
        response.put("realizedVol63d", row.getRealizedVol63d());
        response.put("volatilityRegime", row.getVolatilityRegime());
        response.put("volBandLow", row.getVolBandLow());
        response.put("volBandHigh", row.getVolBandHigh());
        response.put("bandHitRateTrailing90d", row.getBandHitRateTrailing90d());
        // HAR-RV fields: present in schema, unused in Phase 2.  Phase 3 will populate.
        response.put("harRvForecast1d", row.getHarRvForecast1d());
        response.put("harRvModelVersion", row.getHarRvModelVersion());
        response.put("computedAt", row.getComputedAt() == null ? null : row.getComputedAt().toString());
        return response;
    }
}
