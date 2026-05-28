package com.summer.stockproject.dao;

import com.summer.stockproject.entity.VolatilityModelForecast;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface VolatilityModelForecastRepository extends JpaRepository<VolatilityModelForecast, Long> {

    List<VolatilityModelForecast> findBySymbolOrderByModelNameAscAsOfDateDescTargetDateDesc(String symbol);
}
