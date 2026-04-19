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
 * Legacy compatibility shim for the /single-stock/* routes.
 *
 * Kept for backward compatibility with old bookmarks and the standalone
 * single-day input form. Not the main stock chart controller — see
 * {@link StockController} for the generic per-symbol chart pages.
 *
 * Responsibilities:
 *   - GET  /single-stock/aapl    — 302 redirect to /stock/AAPL (preserves query params)
 *   - GET  /single-stock/single  — renders the single-day input form
 *   - POST /single-stock/single  — handles the input form submission
 *   - GET  /single-stock/test    — 302 redirect to /
 */
@Controller
@RequestMapping("/single-stock")
public class LegacySingleStockController {

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
