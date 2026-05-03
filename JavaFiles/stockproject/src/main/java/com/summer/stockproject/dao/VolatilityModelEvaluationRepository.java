package com.summer.stockproject.dao;

import com.summer.stockproject.entity.VolatilityModelEvaluation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface VolatilityModelEvaluationRepository extends JpaRepository<VolatilityModelEvaluation, Long> {

    List<VolatilityModelEvaluation> findBySymbolOrderByModelNameAscEvalWindowEndDesc(String symbol);
}
