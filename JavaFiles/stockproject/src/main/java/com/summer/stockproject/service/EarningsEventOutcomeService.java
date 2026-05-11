package com.summer.stockproject.service;

import com.summer.stockproject.entity.EarningsEventOutcome;

import java.util.List;
import java.util.Map;

public interface EarningsEventOutcomeService {

    List<EarningsEventOutcome> getBySymbol(String symbol);

    EarningsEventOutcome getBySymbolAndPeriod(String symbol, String period);

    Map<String, Object> getAggregateAnalysis(
            String bucket,
            String window,
            String symbol,
            String symbols,
            String quality,
            int minBucketSize,
            int bootstrapSamples
    );
}
