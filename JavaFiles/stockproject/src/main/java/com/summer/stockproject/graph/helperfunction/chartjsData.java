package com.summer.stockproject.graph.helperfunction;

import com.summer.stockproject.graph.entity.AAPL;

import java.util.ArrayList;
import java.util.List;

public class chartjsData {

    private List<ArrayList<Double>> price;

    private List<Long> dateInSecond;



    public chartjsData(List<AAPL> dataList) {
        price = new ArrayList<>();
        dateInSecond = new ArrayList<>();
        for (AAPL apple : dataList) {
            ArrayList<Double> templist = new ArrayList<Double>();
            templist.add(apple.getMinuteOpen());
            templist.add(apple.getMinuteHigh());
            templist.add(apple.getMinuteLow());
            templist.add(apple.getIntminuteClose());
            //System.out.println("apple");
            price.add(templist);
            dateInSecond.add(apple.getTimePoint().getTime());
            // System.out.println();
      }
    }

    public List<ArrayList<Double>> getPrice() {
        return price;
    }

    public List<Long> getDateInSecond() {
        return dateInSecond;
    }
}
