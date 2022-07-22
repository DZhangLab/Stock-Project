package com.summer.stockproject.controller;

import com.summer.stockproject.entity.timestamptable;
import com.summer.stockproject.service.timestampService;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;

@Controller
@RequestMapping("/test")
public class timestampController {
    private timestampService timestampservice;

    public timestampController(timestampService timestampService) {
        this.timestampservice = timestampService;
    }


    @GetMapping("/timestamp")
    public String timestamp() {
        List<timestamptable> list = timestampservice.findAll();
        System.out.println(list.get(0));

        return "redirect:/";
    }
}
