package com.summer.stockproject.graph.controller;

import com.summer.stockproject.graph.entity.companyNames;
import com.summer.stockproject.graph.entity.timestamptable;
import com.summer.stockproject.graph.helperfunction.chartjsData;
import com.summer.stockproject.graph.helperfunction.chartjsDataNew;
import com.summer.stockproject.graph.service.companyNameService;
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
@RequestMapping("/graph")
public class timestampController {
    private timestampService timestampservice;

    private companyNameService companyNameService;


    public timestampController(timestampService timestampService,companyNameService companyNameService) {
        this.companyNameService = companyNameService;
        this.timestampservice = timestampService;

    }
    @GetMapping("/test")
    public String test() {
        System.out.println(companyNameService.findBycompanyName("AAP"));
        return "redirect:/";
    }

    @GetMapping("/timestamp")
    public String timestamp(Model theModel) throws ParseException {
        //List<timestamptable> list = timestampservice.findAll();
        //System.out.println(list.get(0));
        Date startDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-6-30 9:30:00");
        Date endDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2022-6-30 15:59:00");
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());
        String name = "amazon";
        List<timestamptable> list1 = timestampservice.findByStartDateBetween(sqltimestart,sqltimeend, name);
       // System.out.println(list1);
        chartjsDataNew listData = new chartjsDataNew(list1);
        theModel.addAttribute("apple", listData.getPrice());
        theModel.addAttribute("timepoint", listData.getDateInSecond());
        //return "redirect:/";
        return "graphpages/singlegraph";
    }

    @PostMapping("/single")
    public String save(@RequestParam(name = "date") String date, @RequestParam(name = "browser") String browser,  Model theModel) throws ParseException {
        //System.out.println(date);
        //System.out.println(browser);
        if (date == "" || browser == "") {
            System.out.println("test");
            List<companyNames> companyList = companyNameService.findAll();
            theModel.addAttribute("companyList", companyList);
            theModel.addAttribute("empty", true);
            return "graphpages/graph-page";
        }
        companyNames exist = companyNameService.findBycompanyName(browser);
        System.out.println(exist);
        if (exist == null) {
            List<companyNames> companyList = companyNameService.findAll();
            theModel.addAttribute("companyList", companyList);
            theModel.addAttribute("exist", true);
            return "graphPages/graph-page";
        }
        String startD = date + " 9:30:00";
        String endD = date + " 15:59:00";
        Date startDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse(startD);
        Date endDate = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse(endD);
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());

        List<timestamptable> list1 = timestampservice.findByStartDateBetween(sqltimestart,sqltimeend, browser);
        if (list1.isEmpty()) {
            List<companyNames> companyList = companyNameService.findAll();
            theModel.addAttribute("companyList", companyList);
            theModel.addAttribute("errorstatus", true);
            return "graphpages/graph-page";
        }
        //System.out.println(list1);
        chartjsDataNew listData = new chartjsDataNew(list1);
        theModel.addAttribute("apple", listData.getPrice());
        theModel.addAttribute("timepoint", listData.getDateInSecond());
        return "graphpages/singlegraph";
    }
}
