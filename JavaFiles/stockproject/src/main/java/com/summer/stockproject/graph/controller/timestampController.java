package com.summer.stockproject.graph.controller;

import com.summer.stockproject.graph.entity.timestamptable;
import com.summer.stockproject.graph.helperfunction.chartjsData;
import com.summer.stockproject.graph.helperfunction.chartjsDataNew;
import com.summer.stockproject.graph.service.timestampService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.sql.Timestamp;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;

@Controller
@RequestMapping("/test")
public class timestampController {
    private timestampService timestampservice;

    public timestampController(timestampService timestampService) {
        this.timestampservice = timestampService;
    }


    @GetMapping("/timestamp")
    public String timestamp(Model theModel) throws ParseException {
        //List<timestamptable> list = timestampservice.findAll();
        //System.out.println(list.get(0));
        Date startDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-6-30 9:30:00");
        Date endDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-6-30 15:59:00");
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());

        List<timestamptable> list1 = timestampservice.findByStartDateBetween(sqltimestart,sqltimeend);
        System.out.println(list1);
        chartjsDataNew listData = new chartjsDataNew(list1);
        theModel.addAttribute("apple", listData.getPrice());
        theModel.addAttribute("timepoint", listData.getDateInSecond());
        //return "redirect:/";
        return "graphpages/graph-page";
    }

    @PostMapping("/single")
    public String save(@RequestParam(name = "date") String date, Model theModel) throws ParseException {
        System.out.println(date);
        Date startDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse(date + " 9:30:00");
        Date endDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse(date + " 15:59:00");
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());

        List<timestamptable> list1 = timestampservice.findByStartDateBetween(sqltimestart,sqltimeend);
        System.out.println(list1);
        chartjsDataNew listData = new chartjsDataNew(list1);
        theModel.addAttribute("apple", listData.getPrice());
        theModel.addAttribute("timepoint", listData.getDateInSecond());
        return "graphpages/singlegraph";
    }
}
