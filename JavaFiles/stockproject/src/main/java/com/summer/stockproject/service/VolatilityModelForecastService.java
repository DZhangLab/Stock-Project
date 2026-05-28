package com.summer.stockproject.service;

import com.summer.stockproject.entity.VolatilityModelForecast;

import java.util.List;

public interface VolatilityModelForecastService {

    /**
     * Return the latest forecast row per model for the given symbol.
     */
    List<VolatilityModelForecast> getLatestBySymbol(String symbol);
}
