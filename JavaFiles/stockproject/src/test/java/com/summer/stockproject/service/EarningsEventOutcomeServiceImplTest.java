package com.summer.stockproject.service;

import com.summer.stockproject.dao.EarningsEventOutcomeRepository;
import com.summer.stockproject.dao.EarningsToneIndexProjection;
import com.summer.stockproject.entity.EarningsEventOutcome;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class EarningsEventOutcomeServiceImplTest {

    @Mock
    private EarningsEventOutcomeRepository repository;

    @Test
    void attachesExistingNumericToneIndexByNormalizedPeriod() {
        EarningsEventOutcome matched = outcome("FY2025Q1");
        EarningsEventOutcome missing = outcome("2024Q4");
        when(repository.findBySymbolOrderByEventDateDesc("AAPL"))
                .thenReturn(Arrays.asList(matched, missing));
        when(repository.findToneIndexesBySymbol("AAPL"))
                .thenReturn(Arrays.asList(toneIndex("2025Q1", "0.7184")));

        List<EarningsEventOutcome> rows =
                new EarningsEventOutcomeServiceImpl(repository).getBySymbol(" aapl ");

        assertEquals(new BigDecimal("0.7184"), rows.get(0).getAiToneIndex());
        assertNull(rows.get(1).getAiToneIndex());
    }

    private EarningsEventOutcome outcome(String period) {
        EarningsEventOutcome row = new EarningsEventOutcome();
        row.setNormalizedFiscalPeriodLabel(period);
        return row;
    }

    private EarningsToneIndexProjection toneIndex(String period, String value) {
        return new EarningsToneIndexProjection() {
            @Override
            public String getNormalizedFiscalPeriodLabel() {
                return period;
            }

            @Override
            public BigDecimal getAiToneIndex() {
                return new BigDecimal(value);
            }
        };
    }
}
