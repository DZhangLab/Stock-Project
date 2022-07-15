package com.summer.stockproject.controller;

import com.summer.stockproject.entity.AAPL;
import com.summer.stockproject.service.AAPLService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.sql.Timestamp;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@Controller
@RequestMapping("/single-stock")
public class AAPLController {
    private AAPLService AAPLSerivce;

    @Autowired
    public AAPLController(AAPLService AAPLSerivce) {
        this.AAPLSerivce = AAPLSerivce;
    }

    @GetMapping("/aapl")
    public String getapple(Model theModel) throws ParseException {
//        List<AAPL> temp = AAPLSerivce.findAll();
//        for (AAPL apple : temp) {
//
//            System.out.println(apple);
//
//        }

        System.out.println("tehethehrlerhkherekhrkherhlekrehrklerh;erhl;hker");
        Date startDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-7-1 14:30:00");
        Date endDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-7-2 14:30:00");
        //Timestamp sqltime = new Timestamp(test1.getTime());
//
        LocalDateTime dateRetriving = LocalDateTime.of(2021,7,1,14,30,0);
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());


        System.out.println(sqltimestart);

        List<AAPL> test = AAPLSerivce.findByStartDateBetween(sqltimestart,sqltimeend);
        System.out.println(test);

        // set time point list for the chart js need
        // set the stock point for chart js
        List<ArrayList<Double>> pricepoint = new ArrayList<ArrayList<Double>>();
        List<Long> timepoint = new ArrayList<>();

        for (AAPL apple : test) {
            ArrayList<Double> templist = new ArrayList<Double>();
            templist.add(apple.getMinuteOpen());
            templist.add(apple.getMinuteHigh());
            templist.add(apple.getMinuteLow());
            templist.add(apple.getIntminuteClose());
            //System.out.println("apple");
            pricepoint.add(templist);
            timepoint.add(apple.getTimePoint().getTime());
            // System.out.println();

        }




        // render the lists to the html
        theModel.addAttribute("apple", pricepoint);
        theModel.addAttribute("timepoint", timepoint);

        System.out.println(timepoint);

        return "graphpages/graph-page";
    }

    @GetMapping("/test")
    public String gettest() {

        System.out.println(AAPLSerivce.getById(1));
        return "redirect:/";
    }
}
