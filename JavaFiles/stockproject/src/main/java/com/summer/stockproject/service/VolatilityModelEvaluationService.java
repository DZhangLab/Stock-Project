package com.summer.stockproject.service;

import com.summer.stockproject.entity.VolatilityModelEvaluation;

import java.util.List;

public interface VolatilityModelEvaluationService {

    /**
     * Return the latest evaluation row per model for the given symbol.
     */
    List<VolatilityModelEvaluation> getLatestBySymbol(String symbol);
}
