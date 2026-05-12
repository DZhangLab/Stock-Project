package com.summer.stockproject.helperfunction;

import com.summer.stockproject.entity.IntradayBar;

import java.math.BigDecimal;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

public class StockChartData {

    private static final DateTimeFormatter WALL_CLOCK_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private List<ArrayList<Double>> price;

    private List<String> dateInSecond;

    public StockChartData(List<IntradayBar> dataList) {
        price = new ArrayList<>();
        dateInSecond = new ArrayList<>();
        for (IntradayBar bar : dataList) {
            ArrayList<Double> templist = new ArrayList<Double>();
            templist.add(toDouble(bar.getMinuteOpen()));
            templist.add(toDouble(bar.getMinuteHigh()));
            templist.add(toDouble(bar.getMinuteLow()));
            templist.add(toDouble(bar.getMinuteClose()));
            price.add(templist);
            dateInSecond.add(bar.getTimePoint().toLocalDateTime().format(WALL_CLOCK_FORMAT));
      }
    }

    private double toDouble(BigDecimal value) {
        return value == null ? 0.0 : value.doubleValue();
    }

    public List<ArrayList<Double>> getPrice() {
        return price;
    }

    public List<String> getDateInSecond() {
        return dateInSecond;
    }
}
