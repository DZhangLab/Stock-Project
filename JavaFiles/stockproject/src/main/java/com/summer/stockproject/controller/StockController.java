package com.summer.stockproject.controller;

import com.summer.stockproject.entity.AAPL;
import com.summer.stockproject.helperfunction.chartjsData;
import com.summer.stockproject.service.AAPLService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.sql.Timestamp;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

@Controller
@RequestMapping("/stock")
public class StockController {
    
    private AAPLService aaplService;
    
    @Autowired
    public StockController(AAPLService aaplService) {
        this.aaplService = aaplService;
    }
    
    /**
     * Universal stock chart page - supports any stock symbol and date range
     * Usage: /stock/{symbol}?start=2025-11-10 09:30:00&end=2025-11-10 16:00:00
     */
    @GetMapping("/{symbol}")
    public String getStockChart(
            @PathVariable String symbol,
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end,
            Model model) throws ParseException {
        
        // Normalize stock symbol (handle special characters, e.g., BRK.B -> BRKB)
        String normalizedSymbol = symbol.toUpperCase().replace(".", "").replace("/", "");
        
        // Handle MySQL reserved words (same as Python normalize_table_name)
        if (normalizedSymbol.equals("NOW")) {
            normalizedSymbol = "NOW1";
        } else if (normalizedSymbol.equals("ALL")) {
            normalizedSymbol = "ALL1";
        } else if (normalizedSymbol.equals("KEYS")) {
            normalizedSymbol = "KEYS1";
        } else if (normalizedSymbol.equals("KEY")) {
            normalizedSymbol = "KEY1";
        }
        
        // Default date: if not specified, use the most recent day's data
        String startDateStr = start != null ? start.replace("T", " ").replace("/", "-") : "2025-11-11 09:30:00";
        String endDateStr = end != null ? end.replace("T", " ").replace("/", "-") : "2025-11-11 16:00:00";
        
        // Parse date - supports multiple formats
        Date startDate = parseDate(startDateStr, true);  // true means start date
        Date endDate = parseDate(endDateStr, false);     // false means end date
        Timestamp sqlStart = new Timestamp(startDate.getTime());
        Timestamp sqlEnd = new Timestamp(endDate.getTime());
        
        // Format date string for display
        SimpleDateFormat displayFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        startDateStr = displayFormat.format(startDate);
        endDateStr = displayFormat.format(endDate);
        
        // Use universalfind method to query any stock table (with date range)
        List<AAPL> filteredData = aaplService.universalfind(normalizedSymbol, sqlStart, sqlEnd);
        
        // Prepare chart data
        chartjsData listData = new chartjsData(filteredData);
        
        model.addAttribute("apple", listData.getPrice());
        model.addAttribute("timepoint", listData.getDateInSecond());
        model.addAttribute("symbol", symbol.toUpperCase());
        model.addAttribute("startDate", startDateStr);
        model.addAttribute("endDate", endDateStr);
        model.addAttribute("dataCount", filteredData.size());
        model.addAttribute("hasData", filteredData.size() > 0);
        
        return "graphpages/graph-page";
    }
    
    /**
     * Parse date string, supports multiple formats
     * @param dateStr Date string
     * @param isStartDate true means start date (default 09:30:00), false means end date (default 16:00:00)
     */
    private Date parseDate(String dateStr, boolean isStartDate) {
        String defaultDate = isStartDate ? "2025-11-11 09:30:00" : "2025-11-11 16:00:00";
        
        if (dateStr == null || dateStr.trim().isEmpty()) {
            try {
                return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(defaultDate);
            } catch (ParseException e) {
                return new Date();
            }
        }
        
        // Normalize date string (use - as separator)
        dateStr = dateStr.replace("/", "-").trim();
        
        // Supported date format list (sorted by priority)
        String[] patterns = {
            "yyyy-MM-dd HH:mm:ss",  // Full format
            "yyyy-MM-dd HH:mm",      // Without seconds
            "yyyy-MM-dd"             // Date only
        };
        
        for (String pattern : patterns) {
            try {
                SimpleDateFormat sdf = new SimpleDateFormat(pattern);
                sdf.setLenient(false);  // Strict mode
                Date date = sdf.parse(dateStr);
                
                // If only date, add default time
                if (pattern.equals("yyyy-MM-dd")) {
                    String timeStr = isStartDate ? " 09:30:00" : " 16:00:00";
                    String fullDateStr = new SimpleDateFormat("yyyy-MM-dd").format(date) + timeStr;
                    return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(fullDateStr);
                }
                
                // If no seconds, add seconds
                if (pattern.equals("yyyy-MM-dd HH:mm")) {
                    String formatted = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(date);
                    return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(formatted);
                }
                
                return date;
            } catch (ParseException e) {
                // Continue to try next format
            }
        }
        
        // If all formats fail, return default date
        try {
            return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(defaultDate);
        } catch (ParseException e) {
            return new Date();
        }
    }
    
    /**
     * Stock selection page - lists all available stocks
     */
    @GetMapping("/list")
    public String listStocks(Model model) {
        return "graphpages/stock-list";
    }
    
    /**
     * Handle form submission - redirect to stock chart page
     */
    @GetMapping("/view")
    public String viewStock(
            @RequestParam String symbol,
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end) {
        
        StringBuilder url = new StringBuilder("/stock/").append(symbol);
        if (start != null && !start.isEmpty()) {
            url.append("?start=").append(start.replace("T", " "));
            if (end != null && !end.isEmpty()) {
                url.append("&end=").append(end.replace("T", " "));
            }
        } else if (end != null && !end.isEmpty()) {
            url.append("?end=").append(end.replace("T", " "));
        }
        
        return "redirect:" + url.toString();
    }
}

