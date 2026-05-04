package com.summer.stockproject.service;

import com.summer.stockproject.entity.EarningsEventOutcome;

import java.util.List;

public interface EarningsEventOutcomeService {

    List<EarningsEventOutcome> getBySymbol(String symbol);

    EarningsEventOutcome getBySymbolAndPeriod(String symbol, String period);
}
