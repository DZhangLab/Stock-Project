package com.summer.stockproject.graph.controller;

import com.summer.stockproject.graph.entity.AAPL;
import com.summer.stockproject.graph.entity.companyNames;
import com.summer.stockproject.graph.entity.timestamptable;
import com.summer.stockproject.graph.helperfunction.chartjsData;
import com.summer.stockproject.graph.helperfunction.chartjsDataNew;
import com.summer.stockproject.graph.helperfunction.inputDate;
import com.summer.stockproject.graph.service.AAPLService;
import com.summer.stockproject.graph.service.companyNameService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.sql.Timestamp;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;

@Controller
@RequestMapping("/single-stock")
public class AAPLController {
    private AAPLService AAPLSerivce;
    private companyNameService companyNameService;


    @Autowired
    public AAPLController(AAPLService AAPLSerivce,companyNameService companyNameSerivce) {
        this.companyNameService = companyNameSerivce;
        this.AAPLSerivce = AAPLSerivce;
    }


    @GetMapping("/aapl")
    public String getapple(Model theModel)  {

        //set the time range as sql time stamp
        List<companyNames> companyList = companyNameService.findAll();
        theModel.addAttribute("companyList", companyList);
        return "graphpages/graph-page";
    }

    @GetMapping("/single")
    public String gettest(Model model) {
        inputDate inputDate = new inputDate();

        model.addAttribute("inputDate",inputDate);
        //System.out.println(AAPLSerivce.getById(1));
        return "graphpages/singleday";
    }






    @GetMapping("/header")
    public String header() {
        return "fragments/header";
    }

    @PostMapping("/test")
    public String testsubmit(@RequestParam(name = "browser") String browser) {
        System.out.println(browser);
        return "redirect:/";
    }




}
