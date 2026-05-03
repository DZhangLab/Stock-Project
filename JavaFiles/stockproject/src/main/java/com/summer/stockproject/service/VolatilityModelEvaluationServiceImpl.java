package com.summer.stockproject.service;

import com.summer.stockproject.dao.VolatilityModelEvaluationRepository;
import com.summer.stockproject.entity.VolatilityModelEvaluation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class VolatilityModelEvaluationServiceImpl implements VolatilityModelEvaluationService {

    private final VolatilityModelEvaluationRepository repository;

    @Autowired
    public VolatilityModelEvaluationServiceImpl(VolatilityModelEvaluationRepository repository) {
        this.repository = repository;
    }

    @Override
    public List<VolatilityModelEvaluation> getLatestBySymbol(String symbol) {
        if (symbol == null) {
            return Collections.emptyList();
        }
        String normalized = symbol.trim().toUpperCase();
        if (normalized.isEmpty()) {
            return Collections.emptyList();
        }

        List<VolatilityModelEvaluation> rows = repository.findBySymbolOrderByModelNameAscEvalWindowEndDesc(normalized);
        if (rows == null || rows.isEmpty()) {
            return Collections.emptyList();
        }

        Map<String, VolatilityModelEvaluation> latestByModel = new LinkedHashMap<>();
        for (VolatilityModelEvaluation row : rows) {
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
