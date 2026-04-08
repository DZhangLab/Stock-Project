package com.summer.stockproject.controller;

import com.summer.stockproject.helperfunction.inputDate;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * Legacy controller kept for backward compatibility.
 * Redirects old /single-stock/aapl to the generic /stock/AAPL route.
 * Retains /single-stock/single and /single-stock/test endpoints.
 */
@Controller
@RequestMapping("/single-stock")
public class AAPLController {

    @GetMapping("/aapl")
    public String legacyAapl(
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end) {
        StringBuilder redirect = new StringBuilder("redirect:/stock/AAPL");
        if (start != null || end != null) {
            redirect.append("?");
            if (start != null) {
                redirect.append("start=").append(start);
                if (end != null) redirect.append("&");
            }
            if (end != null) {
                redirect.append("end=").append(end);
            }
        }
        return redirect.toString();
    }

    @GetMapping("/single")
    public String getSingle(Model model) {
        model.addAttribute("inputDate", new inputDate());
        return "graphpages/singleday";
    }

    @PostMapping("/single")
    public String postSingle(@ModelAttribute("inputDate") inputDate inputDate) {
        System.out.println(inputDate.getDay());
        return "index";
    }

    @GetMapping("/test")
    public String test() {
        return "redirect:/";
    }
}
