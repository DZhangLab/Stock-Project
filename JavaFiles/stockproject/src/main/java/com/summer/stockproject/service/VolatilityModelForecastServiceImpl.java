package com.summer.stockproject.service;

import com.summer.stockproject.dao.VolatilityModelForecastRepository;
import com.summer.stockproject.entity.VolatilityModelForecast;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class VolatilityModelForecastServiceImpl implements VolatilityModelForecastService {

    private final VolatilityModelForecastRepository repository;

    @Autowired
    public VolatilityModelForecastServiceImpl(VolatilityModelForecastRepository repository) {
        this.repository = repository;
    }

    @Override
    public List<VolatilityModelForecast> getLatestBySymbol(String symbol) {
        if (symbol == null) {
            return Collections.emptyList();
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return Collections.emptyList();
        }

        List<VolatilityModelForecast> rows = repository.findBySymbolOrderByModelNameAscAsOfDateDescTargetDateDesc(normalized);
        if (rows == null || rows.isEmpty()) {
            return Collections.emptyList();
        }

        Map<String, VolatilityModelForecast> latestByModel = new LinkedHashMap<>();
        for (VolatilityModelForecast row : rows) {
            if (row == null || row.getModelName() == null) {
                continue;
            }
            if (!latestByModel.containsKey(row.getModelName())) {
                latestByModel.put(row.getModelName(), row);
            }
        }
        return new ArrayList<>(latestByModel.values());
    }
}
