package com.summer.stockproject.helperfunction;

import com.summer.stockproject.entity.DailyQuote;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

public class DailyChartData {

    private List<ArrayList<Double>> price;
    private List<Long> dateInSecond;

    public DailyChartData(List<DailyQuote> dataList) {
        price = new ArrayList<>();
        dateInSecond = new ArrayList<>();
        for (DailyQuote quote : dataList) {
            ArrayList<Double> ohlc = new ArrayList<>();
            ohlc.add(toDouble(quote.getOpen()));
            ohlc.add(toDouble(quote.getHigh()));
            ohlc.add(toDouble(quote.getLow()));
            ohlc.add(toDouble(quote.getClose()));
            price.add(ohlc);

            // Parse "yyyy-MM-dd" to epoch millis at midnight UTC
            LocalDate date = LocalDate.parse(quote.getDatetime());
            long epochMs = date.atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli();
            dateInSecond.add(epochMs);
        }
    }

    private double toDouble(BigDecimal value) {
        return value == null ? 0.0 : value.doubleValue();
    }

    public List<ArrayList<Double>> getPrice() {
        return price;
    }

    public List<Long> getDateInSecond() {
        return dateInSecond;
    }
}
