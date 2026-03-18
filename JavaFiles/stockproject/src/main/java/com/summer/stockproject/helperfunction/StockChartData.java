package com.summer.stockproject.helperfunction;

import com.summer.stockproject.entity.IntradayBar;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

public class StockChartData {

    private List<ArrayList<Double>> price;

    private List<Long> dateInSecond;

    public StockChartData(List<IntradayBar> dataList) {
        price = new ArrayList<>();
        dateInSecond = new ArrayList<>();
        for (IntradayBar bar : dataList) {
            ArrayList<Double> templist = new ArrayList<Double>();
            templist.add(toDouble(bar.getMinuteOpen()));
            templist.add(toDouble(bar.getMinuteHigh()));
            templist.add(toDouble(bar.getMinuteLow()));
            templist.add(toDouble(bar.getIntminuteClose()));
            price.add(templist);
            dateInSecond.add(bar.getTimePoint().getTime());
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
