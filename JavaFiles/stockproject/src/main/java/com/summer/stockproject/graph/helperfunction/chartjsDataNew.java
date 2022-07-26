package com.summer.stockproject.graph.helperfunction;

import com.summer.stockproject.graph.entity.timestamptable;

import java.util.ArrayList;
import java.util.List;

public class chartjsDataNew {
    private List<ArrayList<Double>> price;

    private List<Long> dateInSecond;



    public chartjsDataNew(List<timestamptable> dataList) {
        price = new ArrayList<>();
        dateInSecond = new ArrayList<>();
        for (timestamptable timestamptable : dataList) {
            ArrayList<Double> templist = new ArrayList<Double>();
            templist.add(timestamptable.getMinuteOpen());
            templist.add(timestamptable.getMinuteHigh());
            templist.add(timestamptable.getMinuteLow());
            templist.add(timestamptable.getMinuteclose());
            //System.out.println("apple");
            price.add(templist);
            dateInSecond.add(timestamptable.getMykey().getTimePoint().getTime());
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
