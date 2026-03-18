package com.summer.stockproject.controller;

import com.summer.stockproject.entity.IntradayBar;
import com.summer.stockproject.helperfunction.StockChartData;
import com.summer.stockproject.service.CompanyNewsService;
import com.summer.stockproject.service.IntradayBarService;
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
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.Date;
import java.util.List;

@Controller
@RequestMapping("/stock")
public class StockController {
    
    private final IntradayBarService intradayBarService;
    private final CompanyNewsService companyNewsService;
    
    @Autowired
    public StockController(IntradayBarService intradayBarService, CompanyNewsService companyNewsService) {
        this.intradayBarService = intradayBarService;
        this.companyNewsService = companyNewsService;
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
        
        DefaultRange defaultRange = getDefaultRangeForSymbol(normalizedSymbol);
        
        // Default date: if not specified, use the most recent day's data (or today if no data)
        String startDateStr = start != null ? start.replace("T", " ").replace("/", "-") : defaultRange.startDisplay;
        String endDateStr = end != null ? end.replace("T", " ").replace("/", "-") : defaultRange.endDisplay;
        
        // Parse date - supports multiple formats
        Date startDate = parseDate(startDateStr, true, defaultRange);  // true means start date
        Date endDate = parseDate(endDateStr, false, defaultRange);     // false means end date
        Timestamp sqlStart = new Timestamp(startDate.getTime());
        Timestamp sqlEnd = new Timestamp(endDate.getTime());
        
        // Format date string for display
        SimpleDateFormat displayFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        startDateStr = displayFormat.format(startDate);
        endDateStr = displayFormat.format(endDate);
        
        // Use universalfind method to query any stock table (with date range)
        List<IntradayBar> filteredData = intradayBarService.universalfind(normalizedSymbol, sqlStart, sqlEnd);
        
        // Prepare chart data
        StockChartData listData = new StockChartData(filteredData);
        
        model.addAttribute("apple", listData.getPrice());
        model.addAttribute("timepoint", listData.getDateInSecond());
        model.addAttribute("symbol", symbol.toUpperCase());
        model.addAttribute("startDate", startDateStr);
        model.addAttribute("endDate", endDateStr);
        model.addAttribute("dataCount", filteredData.size());
        model.addAttribute("hasData", !filteredData.isEmpty());
        model.addAttribute("showAppleNews", normalizedSymbol.equals("AAPL"));
        if (normalizedSymbol.equals("AAPL")) {
            model.addAttribute("appleNews", companyNewsService.getRecentAppleNews());
        }
        
        return "graphpages/graph-page";
    }
    
    /**
     * Parse date string, supports multiple formats
     * @param dateStr Date string
     * @param isStartDate true means start date (default 09:30:00), false means end date (default 16:00:00)
     */
    private Date parseDate(String dateStr, boolean isStartDate, DefaultRange defaultRange) {
        if (dateStr == null || dateStr.trim().isEmpty()) {
            return isStartDate ? new Date(defaultRange.start.getTime()) : new Date(defaultRange.end.getTime());
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
                    LocalDate localDate = LocalDate.parse(new SimpleDateFormat("yyyy-MM-dd").format(date));
                    LocalTime time = isStartDate ? defaultRange.startTime : defaultRange.endTime;
                    LocalDateTime dateTime = LocalDateTime.of(localDate, time);
                    return Timestamp.valueOf(dateTime);
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
        return isStartDate ? new Date(defaultRange.start.getTime()) : new Date(defaultRange.end.getTime());
    }
    
    /**
     * Stock selection page - lists all available stocks
     */
    @GetMapping("/list")
    public String listStocks(Model model) {
        DefaultRange defaultRange = getDefaultRangeForSymbol("AAPL");
        model.addAttribute("defaultStartLocal", defaultRange.startLocal);
        model.addAttribute("defaultEndLocal", defaultRange.endLocal);
        model.addAttribute("defaultStartDisplay", defaultRange.startDisplay);
        model.addAttribute("defaultEndDisplay", defaultRange.endDisplay);
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

    private DefaultRange getDefaultRangeForSymbol(String normalizedSymbol) {
        Timestamp latest = null;
        try {
            latest = intradayBarService.getLatestTimePoint(normalizedSymbol);
        } catch (Exception ignored) {
            // Fallback to today if table does not exist or query fails
        }
        
        LocalDate date = latest != null
                ? latest.toLocalDateTime().toLocalDate()
                : LocalDate.now();
        
        LocalTime startTime = LocalTime.of(9, 30);
        LocalTime endTime = LocalTime.of(16, 0);
        
        LocalDateTime startDateTime = LocalDateTime.of(date, startTime);
        LocalDateTime endDateTime = LocalDateTime.of(date, endTime);
        
        SimpleDateFormat displayFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        SimpleDateFormat inputFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm");
        
        DefaultRange range = new DefaultRange();
        range.start = Timestamp.valueOf(startDateTime);
        range.end = Timestamp.valueOf(endDateTime);
        range.startTime = startTime;
        range.endTime = endTime;
        range.startDisplay = displayFormat.format(range.start);
        range.endDisplay = displayFormat.format(range.end);
        range.startLocal = inputFormat.format(range.start);
        range.endLocal = inputFormat.format(range.end);
        
        return range;
    }

    private static class DefaultRange {
        private Timestamp start;
        private Timestamp end;
        private LocalTime startTime;
        private LocalTime endTime;
        private String startDisplay;
        private String endDisplay;
        private String startLocal;
        private String endLocal;
    }
}

