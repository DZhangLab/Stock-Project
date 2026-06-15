package com.summer.stockproject.dao;

import java.math.BigDecimal;

public interface EarningsToneIndexProjection {

    String getNormalizedFiscalPeriodLabel();

    BigDecimal getAiToneIndex();
}
