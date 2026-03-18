package com.summer.stockproject.controller;

import com.summer.stockproject.entity.IntradayBar;
import com.summer.stockproject.helperfunction.StockChartData;
import com.summer.stockproject.helperfunction.inputDate;
import com.summer.stockproject.service.CompanyNewsService;
import com.summer.stockproject.service.IntradayBarService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
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
@RequestMapping("/single-stock")
public class AAPLController {
    private final IntradayBarService intradayBarService;
    private final CompanyNewsService companyNewsService;
    @Autowired
    public AAPLController(IntradayBarService intradayBarService, CompanyNewsService companyNewsService) {
        this.intradayBarService = intradayBarService;
        this.companyNewsService = companyNewsService;
    }

    @GetMapping("/aapl")
    public String getapple(
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end,
            Model theModel) throws ParseException {

        DefaultRange defaultRange = getDefaultRangeForAapl();

        // Set the time range as SQL timestamp - supports date parameters, defaults to latest available date
        String startDateStr = start != null ? start : defaultRange.startDisplay;
        String endDateStr = end != null ? end : defaultRange.endDisplay;
        
        Date startDate = parseDate(startDateStr, true, defaultRange);
        Date endDate = parseDate(endDateStr, false, defaultRange);
        Timestamp sqltimestart = new Timestamp(startDate.getTime());
        Timestamp sqltimeend = new Timestamp(endDate.getTime());

        // get data base on the set time range
        List<IntradayBar> bars = intradayBarService.findByStartDateBetween(sqltimestart, sqltimeend);

        // set time point list for the chart js need
        // set the stock point for chart js

        StockChartData listData = new StockChartData(bars);
//
//        ####  previous code, the new code is using the helper method from helperfunction package
//        List<ArrayList<Double>> pricepoint = new ArrayList<ArrayList<Double>>();
//        List<Long> timepoint = new ArrayList<>();
//        for (AAPL apple : test) {
//            ArrayList<Double> templist = new ArrayList<Double>();
//            templist.add(apple.getMinuteOpen());
//            templist.add(apple.getMinuteHigh());
//            templist.add(apple.getMinuteLow());
//            templist.add(apple.getIntminuteClose());
//            //System.out.println("apple");
//            pricepoint.add(templist);
//            timepoint.add(apple.getTimePoint().getTime());
//            // System.out.println();
//
//        }

        // render the lists to the html
        theModel.addAttribute("apple", listData.getPrice());
        theModel.addAttribute("timepoint", listData.getDateInSecond());
        theModel.addAttribute("symbol", "AAPL");
        theModel.addAttribute("startDate", startDateStr);
        theModel.addAttribute("endDate", endDateStr);
        theModel.addAttribute("dataCount", bars.size());
        theModel.addAttribute("hasData", !bars.isEmpty());
        theModel.addAttribute("showAppleNews", true);
        theModel.addAttribute("appleNews", companyNewsService.getRecentAppleNews());

        return "graphpages/graph-page";
    }

    @GetMapping("/single")
    public String gettest(Model model) {
        inputDate inputDate = new inputDate();

        model.addAttribute("inputDate",inputDate);
        //System.out.println(AAPLSerivce.getById(1));
        return "graphpages/singleday";
    }

    @PostMapping("/single")
    public String save(@ModelAttribute("inputDate") inputDate inputDate) {
        System.out.println(inputDate.getDay());
        return "index";
    }


    @GetMapping("/test")
    public String unifind() throws ParseException {
        DefaultRange defaultRange = getDefaultRangeForSymbol("AMZN");
        List<IntradayBar> list = intradayBarService.universalfind("AMZN", defaultRange.start, defaultRange.end);
        System.out.println(list);

        return "redirect:/";
    }

    private Date parseDate(String dateStr, boolean isStartDate, DefaultRange defaultRange) {
        if (dateStr == null || dateStr.trim().isEmpty()) {
            return isStartDate ? new Date(defaultRange.start.getTime()) : new Date(defaultRange.end.getTime());
        }

        // Normalize date string (use - as separator)
        dateStr = dateStr.replace("/", "-").trim();

        String[] patterns = {
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd HH:mm",
            "yyyy-MM-dd"
        };

        for (String pattern : patterns) {
            try {
                SimpleDateFormat sdf = new SimpleDateFormat(pattern);
                sdf.setLenient(false);
                Date date = sdf.parse(dateStr);

                if (pattern.equals("yyyy-MM-dd")) {
                    LocalDate localDate = LocalDate.parse(new SimpleDateFormat("yyyy-MM-dd").format(date));
                    LocalTime time = isStartDate ? defaultRange.startTime : defaultRange.endTime;
                    LocalDateTime dateTime = LocalDateTime.of(localDate, time);
                    return Timestamp.valueOf(dateTime);
                }

                if (pattern.equals("yyyy-MM-dd HH:mm")) {
                    String formatted = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(date);
                    return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(formatted);
                }

                return date;
            } catch (ParseException e) {
                // Continue to try next format
            }
        }

        return isStartDate ? new Date(defaultRange.start.getTime()) : new Date(defaultRange.end.getTime());
    }

    private DefaultRange getDefaultRangeForAapl() {
        return getDefaultRangeForSymbol("AAPL");
    }

    private DefaultRange getDefaultRangeForSymbol(String symbol) {
        Timestamp latest = null;
        try {
            latest = intradayBarService.getLatestTimePoint(symbol);
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

        DefaultRange range = new DefaultRange();
        range.start = Timestamp.valueOf(startDateTime);
        range.end = Timestamp.valueOf(endDateTime);
        range.startTime = startTime;
        range.endTime = endTime;
        range.startDisplay = displayFormat.format(range.start);
        range.endDisplay = displayFormat.format(range.end);

        return range;
    }

    private static class DefaultRange {
        private Timestamp start;
        private Timestamp end;
        private LocalTime startTime;
        private LocalTime endTime;
        private String startDisplay;
        private String endDisplay;
    }


}
