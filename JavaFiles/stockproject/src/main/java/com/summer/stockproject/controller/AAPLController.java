package com.summer.stockproject.controller;

import com.summer.stockproject.entity.AAPL;
import com.summer.stockproject.entity.timestamptable;
import com.summer.stockproject.helperfunction.chartjsData;
import com.summer.stockproject.helperfunction.inputDate;
import com.summer.stockproject.service.AAPLService;
import com.summer.stockproject.service.timestampService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

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
    public String getapple(
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end,
            Model theModel) throws ParseException {

        // Set the time range as SQL timestamp - supports date parameters, defaults to current data date range
        String startDateStr = start != null ? start : "2025-11-11 09:30:00";
        String endDateStr = end != null ? end : "2025-11-11 16:00:00";
        
        Date startDate = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(startDateStr);
        Date endDate = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(endDateStr);
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());

        // get data base on the set time range
        List<AAPL> test = AAPLSerivce.findByStartDateBetween(sqltimestart,sqltimeend);

        // set time point list for the chart js need
        // set the stock point for chart js

        chartjsData listData = new chartjsData(test);
//
//        ####  previous code, the new code is using the helper method from helperfunction package
//        List<ArrayList<Double>> pricepoint = new ArrayList<ArrayList<Double>>();
//        List<Long> timepoint = new ArrayList<>();
//        for (AAPL apple : test) {
//            ArrayList<Double> templist = new ArrayList<Double>();
//            templist.add(apple.getMinuteOpen());
//            templist.add(apple.getMinuteHigh());
//            templist.add(apple.getMinuteLow());
//            templist.add(apple.getIntminuteClose());
//            //System.out.println("apple");
//            pricepoint.add(templist);
//            timepoint.add(apple.getTimePoint().getTime());
//            // System.out.println();
//
//        }

        // render the lists to the html
        theModel.addAttribute("apple", listData.getPrice());
        theModel.addAttribute("timepoint", listData.getDateInSecond());
        theModel.addAttribute("symbol", "AAPL");
        theModel.addAttribute("startDate", startDateStr);
        theModel.addAttribute("endDate", endDateStr);

        return "graphpages/graph-page";
    }

    @GetMapping("/single")
    public String gettest(Model model) {
        inputDate inputDate = new inputDate();

        model.addAttribute("inputDate",inputDate);
        //System.out.println(AAPLSerivce.getById(1));
        return "graphpages/singleday";
    }

    @PostMapping("/single")
    public String save(@ModelAttribute("inputDate") inputDate inputDate) {
        System.out.println(inputDate.getDay());
        return "index";
    }


    @GetMapping("/test")
    public String unifind() throws ParseException {
        Date startDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-6-30 9:30:00");
        Date endDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-6-30 15:59:00");
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());

        List<AAPL> list = AAPLSerivce.universalfind("AMZN", sqltimestart, sqltimeend);
        System.out.println(list);

        return "redirect:/";
    }


}
