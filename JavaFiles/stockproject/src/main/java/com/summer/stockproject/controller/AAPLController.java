package com.summer.stockproject.controller;

import com.summer.stockproject.entity.AAPL;
import com.summer.stockproject.service.AAPLService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

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
    public String getapple() {
        List<AAPL> temp = AAPLSerivce.findAll();
        for (AAPL apple : temp) {
            System.out.println(apple);

        }
        return "redirect:/";
    }

    @GetMapping("/test")
    public String gettest() {

        System.out.println(AAPLSerivce.getById(1));
        return "redirect:/";
    }
}
