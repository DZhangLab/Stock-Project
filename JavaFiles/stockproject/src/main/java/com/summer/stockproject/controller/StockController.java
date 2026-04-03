package com.summer.stockproject.controller;

import com.summer.stockproject.entity.DailyQuote;
import com.summer.stockproject.entity.IntradayBar;
import com.summer.stockproject.helperfunction.DailyChartData;
import com.summer.stockproject.helperfunction.StockChartData;
import com.summer.stockproject.service.CompanyNewsService;
import com.summer.stockproject.service.DailyQuoteService;
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
import java.util.Arrays;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Controller
@RequestMapping("/stock")
public class StockController {
    
    private final IntradayBarService intradayBarService;
    private final DailyQuoteService dailyQuoteService;
    private final CompanyNewsService companyNewsService;

    private static final Set<String> DAILY_RANGES = new HashSet<>(
            Arrays.asList("1M", "3M", "6M", "YTD", "1Y"));

    @Autowired
    public StockController(IntradayBarService intradayBarService,
                           DailyQuoteService dailyQuoteService,
                           CompanyNewsService companyNewsService) {
        this.intradayBarService = intradayBarService;
        this.dailyQuoteService = dailyQuoteService;
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
            @RequestParam(required = false) String range,
            Model model) throws ParseException {

        String displaySymbol = symbol.toUpperCase();

        // Normalize for intraday table names (BRK.B -> BRKB, handle reserved words)
        String normalizedSymbol = displaySymbol.replace(".", "").replace("/", "");
        if (normalizedSymbol.equals("NOW")) {
            normalizedSymbol = "NOW1";
        } else if (normalizedSymbol.equals("ALL")) {
            normalizedSymbol = "ALL1";
        } else if (normalizedSymbol.equals("KEYS")) {
            normalizedSymbol = "KEYS1";
        } else if (normalizedSymbol.equals("KEY")) {
            normalizedSymbol = "KEY1";
        }

        // Explicit start/end takes precedence over range
        boolean hasCustomRange = (start != null && !start.trim().isEmpty())
                || (end != null && !end.trim().isEmpty());

        // Determine which data path to use
        String activeRange = hasCustomRange ? "" : (range != null ? range.toUpperCase() : "1D");
        boolean useDaily = !hasCustomRange && DAILY_RANGES.contains(activeRange);
        boolean use30Min = !hasCustomRange && "1W".equals(activeRange);

        if (useDaily) {
            return handleDailyRange(displaySymbol, normalizedSymbol, activeRange, model);
        } else if (use30Min) {
            return handle30MinRange(displaySymbol, normalizedSymbol, model);
        } else {
            return handleIntradayRange(displaySymbol, normalizedSymbol, activeRange, start, end, model);
        }
    }

    /**
     * Handle 1W using 30-minute aggregated intraday bars.
     * Queries the per-symbol minute table for the last 7 calendar days,
     * then aggregates into half-hour OHLCV bars server-side.
     */
    private String handle30MinRange(String displaySymbol, String normalizedSymbol,
                                     Model model) {
        // Find latest data point to anchor the 1W window
        Timestamp latest = null;
        try {
            latest = intradayBarService.getLatestTimePoint(normalizedSymbol);
        } catch (Exception ignored) {
        }
        if (latest == null) {
            setEmptyModel(model, displaySymbol, "1W", "30min");
            return "graphpages/graph-page";
        }

        LocalDate latestDate = latest.toLocalDateTime().toLocalDate();
        LocalDate startDate = latestDate.minusWeeks(1);

        // Query window: startDate 09:30 through latestDate 16:00
        Timestamp sqlStart = Timestamp.valueOf(startDate.atTime(9, 30));
        Timestamp sqlEnd = Timestamp.valueOf(latestDate.atTime(16, 0));

        List<IntradayBar> aggregated = intradayBarService.findAggregated(
                normalizedSymbol, sqlStart, sqlEnd, 10);

        StockChartData chartData = new StockChartData(aggregated);

        SimpleDateFormat displayFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

        model.addAttribute("apple", chartData.getPrice());
        model.addAttribute("timepoint", chartData.getDateInSecond());
        model.addAttribute("symbol", displaySymbol);
        model.addAttribute("startDate", displayFormat.format(sqlStart));
        model.addAttribute("endDate", displayFormat.format(sqlEnd));
        model.addAttribute("dataCount", aggregated.size());
        model.addAttribute("hasData", !aggregated.isEmpty());
        model.addAttribute("dataGranularity", "30min");
        model.addAttribute("activeRange", "1W");
        model.addAttribute("showAppleNews", normalizedSymbol.equals("AAPL"));
        if (normalizedSymbol.equals("AAPL")) {
            model.addAttribute("appleNews", companyNewsService.getRecentAppleNews());
        }

        return "graphpages/graph-page";
    }

    /**
     * Handle 1M/3M/6M/YTD/1Y ranges using daily data from everydayAfterClose.
     */
    private String handleDailyRange(String displaySymbol, String normalizedSymbol,
                                     String range, Model model) {
        // Use API-format symbol for daily table (e.g., "BRK.B" not "BRKB")
        String apiSymbol = displaySymbol;

        // Find the latest available trading date for this symbol
        String latestDate = dailyQuoteService.getLatestDateForSymbol(apiSymbol);
        if (latestDate == null) {
            // No daily data — show empty state
            setEmptyModel(model, displaySymbol, range, "daily");
            return "graphpages/graph-page";
        }

        LocalDate latest = LocalDate.parse(latestDate);
        LocalDate startDate = computeRangeStart(range, latest);
        String startDateStr = startDate.toString();

        List<DailyQuote> dailyData = dailyQuoteService.findBySymbolAndDateRange(
                apiSymbol, startDateStr, latestDate);

        DailyChartData chartData = new DailyChartData(dailyData);

        model.addAttribute("apple", chartData.getPrice());
        model.addAttribute("timepoint", chartData.getDateInSecond());
        model.addAttribute("symbol", displaySymbol);
        model.addAttribute("startDate", startDateStr);
        model.addAttribute("endDate", latestDate);
        model.addAttribute("dataCount", dailyData.size());
        model.addAttribute("hasData", !dailyData.isEmpty());
        model.addAttribute("dataGranularity", "daily");
        model.addAttribute("activeRange", range);
        model.addAttribute("showAppleNews", normalizedSymbol.equals("AAPL"));
        if (normalizedSymbol.equals("AAPL")) {
            model.addAttribute("appleNews", companyNewsService.getRecentAppleNews());
        }

        return "graphpages/graph-page";
    }

    /**
     * Handle 1D / custom start-end using intraday minute data.
     */
    private String handleIntradayRange(String displaySymbol, String normalizedSymbol,
                                        String activeRange, String start, String end,
                                        Model model) throws ParseException {
        DefaultRange defaultRange = getDefaultRangeForSymbol(normalizedSymbol);

        String startDateStr = start != null ? start.replace("T", " ").replace("/", "-") : defaultRange.startDisplay;
        String endDateStr = end != null ? end.replace("T", " ").replace("/", "-") : defaultRange.endDisplay;

        Date startDate = parseDate(startDateStr, true, defaultRange);
        Date endDate = parseDate(endDateStr, false, defaultRange);
        Timestamp sqlStart = new Timestamp(startDate.getTime());
        Timestamp sqlEnd = new Timestamp(endDate.getTime());

        SimpleDateFormat displayFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        startDateStr = displayFormat.format(startDate);
        endDateStr = displayFormat.format(endDate);

        List<IntradayBar> filteredData = intradayBarService.universalfind(normalizedSymbol, sqlStart, sqlEnd);
        StockChartData listData = new StockChartData(filteredData);

        model.addAttribute("apple", listData.getPrice());
        model.addAttribute("timepoint", listData.getDateInSecond());
        model.addAttribute("symbol", displaySymbol);
        model.addAttribute("startDate", startDateStr);
        model.addAttribute("endDate", endDateStr);
        model.addAttribute("dataCount", filteredData.size());
        model.addAttribute("hasData", !filteredData.isEmpty());
        model.addAttribute("dataGranularity", "minute");
        model.addAttribute("activeRange", activeRange);
        model.addAttribute("showAppleNews", normalizedSymbol.equals("AAPL"));
        if (normalizedSymbol.equals("AAPL")) {
            model.addAttribute("appleNews", companyNewsService.getRecentAppleNews());
        }

        return "graphpages/graph-page";
    }

    private void setEmptyModel(Model model, String symbol, String range, String granularity) {
        model.addAttribute("apple", List.of());
        model.addAttribute("timepoint", List.of());
        model.addAttribute("symbol", symbol);
        model.addAttribute("startDate", "N/A");
        model.addAttribute("endDate", "N/A");
        model.addAttribute("dataCount", 0);
        model.addAttribute("hasData", false);
        model.addAttribute("dataGranularity", granularity);
        model.addAttribute("activeRange", range);
        model.addAttribute("showAppleNews", false);
    }

    /**
     * Compute start date for a given range relative to the latest available date.
     */
    private LocalDate computeRangeStart(String range, LocalDate latest) {
        switch (range) {
            case "1W":  return latest.minusWeeks(1);
            case "1M":  return latest.minusMonths(1);
            case "3M":  return latest.minusMonths(3);
            case "6M":  return latest.minusMonths(6);
            case "YTD": return LocalDate.of(latest.getYear(), 1, 1);
            case "1Y":  return latest.minusYears(1);
            default:    return latest.minusWeeks(1);
        }
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

