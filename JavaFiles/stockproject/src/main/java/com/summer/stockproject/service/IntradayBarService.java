package com.summer.stockproject.service;

import com.summer.stockproject.entity.IntradayBar;

import java.sql.Timestamp;
import java.util.List;

public interface IntradayBarService {

    List<IntradayBar> universalfind(String tablename, Timestamp start, Timestamp end);

    /**
     * Query minute bars and aggregate into N-minute OHLCV bars.
     * Each window is aligned to the session start (09:30) so that
     * e.g. 10-min windows run 09:30-09:39, 09:40-09:49, etc.
     * Open = first bar's open, High = max, Low = min, Close = last bar's close,
     * Volume = sum.  The returned IntradayBar.timePoint is set to the window start.
     */
    List<IntradayBar> findAggregated(String tablename, Timestamp start, Timestamp end, int intervalMinutes);

    Timestamp getLatestTimePoint(String tablename);
}
