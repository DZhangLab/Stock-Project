package com.summer.stockproject.controller;

import com.summer.stockproject.entity.DailyVolatility;
import com.summer.stockproject.entity.VolatilityModelForecast;
import com.summer.stockproject.service.DailyVolatilityService;
import com.summer.stockproject.service.VolatilityModelEvaluationService;
import com.summer.stockproject.service.VolatilityModelForecastService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.Arrays;
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
    private final VolatilityModelForecastService forecastService;

    @Autowired
    public VolatilityController(
            DailyVolatilityService service,
            VolatilityModelEvaluationService evaluationService,
            VolatilityModelForecastService forecastService
    ) {
        this.service = service;
        this.evaluationService = evaluationService;
        this.forecastService = forecastService;
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

    @GetMapping("/model-summary/latest")
    public ResponseEntity<Map<String, Object>> getLatestModelSummary(
            @RequestParam(defaultValue = "AAPL") String symbol) {
        String normalized = symbol == null ? "" : symbol.trim().toUpperCase();
        List<VolatilityModelForecast> forecasts = forecastService.getLatestBySymbol(normalized);
        List<VolatilityModelEvaluation> evaluations = evaluationService.getLatestBySymbol(normalized);

        if (forecasts.isEmpty() && evaluations.isEmpty()) {
            Map<String, Object> notFound = new LinkedHashMap<>();
            notFound.put("symbol", normalized);
            notFound.put("message", "No volatility model summary rows found");
            return ResponseEntity.status(404).body(notFound);
        }

        Map<String, VolatilityModelForecast> forecastByModel = new LinkedHashMap<>();
        for (VolatilityModelForecast row : forecasts) {
            if (row != null && row.getModelName() != null) {
                forecastByModel.put(row.getModelName(), row);
            }
        }

        Map<String, VolatilityModelEvaluation> evaluationByModel = new LinkedHashMap<>();
        for (VolatilityModelEvaluation row : evaluations) {
            if (row != null && row.getModelName() != null) {
                evaluationByModel.put(row.getModelName(), row);
            }
        }

        List<String> orderedModelNames = new ArrayList<>(Arrays.asList(
                "baseline_rolling21",
                "baseline_yesterday_rv",
                "har_rv_v1"
        ));
        for (String modelName : forecastByModel.keySet()) {
            if (!orderedModelNames.contains(modelName)) {
                orderedModelNames.add(modelName);
            }
        }
        for (String modelName : evaluationByModel.keySet()) {
            if (!orderedModelNames.contains(modelName)) {
                orderedModelNames.add(modelName);
            }
        }

        List<Map<String, Object>> models = new ArrayList<>();
        String asOfDate = null;
        String targetDate = null;
        for (String modelName : orderedModelNames) {
            VolatilityModelForecast forecast = forecastByModel.get(modelName);
            VolatilityModelEvaluation evaluation = evaluationByModel.get(modelName);
            if (forecast == null && evaluation == null) {
                continue;
            }
            if (asOfDate == null && forecast != null && forecast.getAsOfDate() != null) {
                asOfDate = forecast.getAsOfDate().toString();
            }
            if (targetDate == null && forecast != null && forecast.getTargetDate() != null) {
                targetDate = forecast.getTargetDate().toString();
            }
            models.add(buildModelSummaryResponse(modelName, forecast, evaluation));
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("symbol", normalized);
        response.put("asOfDate", asOfDate);
        response.put("targetDate", targetDate);
        response.put("count", models.size());
        response.put("models", models);
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

    private Map<String, Object> buildModelSummaryResponse(
            String modelName,
            VolatilityModelForecast forecast,
            VolatilityModelEvaluation evaluation
    ) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("modelName", modelName);
        response.put("displayName", friendlyModelName(modelName));
        response.put("forecastVolAnnualized", forecast == null ? null : forecast.getForecastVolAnnualized());
        response.put("forecastVariance", forecast == null ? null : forecast.getForecastVariance());
        response.put("actualVolAnnualized", forecast == null ? null : forecast.getActualVolAnnualized());
        response.put("actualVariance", forecast == null ? null : forecast.getActualVariance());
        response.put("asOfDate", forecast == null || forecast.getAsOfDate() == null ? null : forecast.getAsOfDate().toString());
        response.put("targetDate", forecast == null || forecast.getTargetDate() == null ? null : forecast.getTargetDate().toString());
        response.put("modelVersion", forecast == null ? null : forecast.getModelVersion());
        response.put("evalWindowStart", evaluation == null || evaluation.getEvalWindowStart() == null ? null : evaluation.getEvalWindowStart().toString());
        response.put("evalWindowEnd", evaluation == null || evaluation.getEvalWindowEnd() == null ? null : evaluation.getEvalWindowEnd().toString());
        response.put("evalWindowDays", evaluation == null ? null : evaluation.getEvalWindowDays());
        response.put("mae", evaluation == null ? null : evaluation.getMae());
        response.put("rmse", evaluation == null ? null : evaluation.getRmse());
        response.put("qlike", evaluation == null ? null : evaluation.getQlike());
        response.put("nObservations", evaluation == null ? null : evaluation.getNObservations());
        response.put(
                "computedAt",
                forecast != null && forecast.getComputedAt() != null
                        ? forecast.getComputedAt().toString()
                        : (evaluation == null || evaluation.getComputedAt() == null ? null : evaluation.getComputedAt().toString())
        );
        return response;
    }

    private String friendlyModelName(String modelName) {
        if ("baseline_rolling21".equals(modelName)) {
            return "21-day rolling baseline";
        }
        if ("baseline_yesterday_rv".equals(modelName)) {
            return "Yesterday RV baseline";
        }
        if ("har_rv_v1".equals(modelName)) {
            return "HAR-RV";
        }
        return modelName == null ? "Unknown" : modelName;
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
