$(document).ready(function () {

  // --- Guard: skip if no data injected by Thymeleaf ---
  if (typeof apple === "undefined" || !apple || apple.length === 0) {
    console.log("No data, skipping chart rendering");
    return;
  }
  if (typeof timepoint === "undefined" || !timepoint || timepoint.length === 0) {
    return;
  }

  var container = document.getElementById("chartContainer");
  if (!container) {
    return;
  }

  // =====================================================
  // Timezone / display-coordinate helper
  //
  // Lightweight Charts renders timestamps as UTC.  Intraday market
  // timestamps arrive as timezone-free ET wall-clock strings from the
  // backend, so we parse those fields directly into a fake-UTC chart
  // coordinate.  This avoids browser/JVM timezone shifts.
  // =====================================================

  function parseETDisplayString(str) {
    if (!str) return null;
    var p = String(str).trim().split(/[- :T]/);
    if (p.length < 5) return null;
    var year = parseInt(p[0], 10);
    var month = parseInt(p[1], 10);
    var day = parseInt(p[2], 10);
    var hour = parseInt(p[3], 10);
    var minute = parseInt(p[4], 10);
    var second = p[5] ? parseInt(p[5], 10) : 0;
    if ([year, month, day, hour, minute, second].some(function(v) { return isNaN(v); })) {
      return null;
    }
    return Date.UTC(
      year,
      month - 1,
      day,
      hour,
      minute,
      second
    ) / 1000;
  }

  var isDaily = (typeof dataGranularity !== "undefined" && dataGranularity === "daily");
  var isMultiDay = (typeof dataGranularity !== "undefined"
      && (dataGranularity === "30min" || dataGranularity === "sampled"));

  // =====================================================
  // 1. Transform backend data into Lightweight Charts format
  //
  //    Backend provides (via Thymeleaf):
  //      apple[i]     = [open, high, low, close]
  //      timepoint[i] = intraday ET wall-clock string, or daily epoch millis
  //
  //    The backend stores OHLC columns per minute bar, but
  //    in practice the source data provides a single price
  //    per timestamp (open == high == low == close).
  //    We use a line series keyed on the close price.
  // =====================================================

  var rawData = [];

  for (var i = 0; i < timepoint.length; i++) {
    // Daily data: timestamps are already midnight UTC — use directly.
    // Intraday: parse ET wall-clock strings to fake-UTC chart seconds.
    var displaySec = isDaily
        ? Math.floor(timepoint[i] / 1000)
        : parseETDisplayString(timepoint[i]);
    if (displaySec === null) {
      continue;
    }
    var c = Number(apple[i][3]); // close price
    rawData.push({ time: displaySec, value: c });
  }

  // --- Deduplicate by timestamp (keep last value per second) ---
  var seen = {};
  var lineData = [];
  for (var i = 0; i < rawData.length; i++) {
    var key = rawData[i].time;
    if (seen[key] !== undefined) {
      lineData[seen[key]] = rawData[i];
    } else {
      seen[key] = lineData.length;
      lineData.push(rawData[i]);
    }
  }

  // --- Sort ascending by time (Lightweight Charts requirement) ---
  lineData.sort(function (a, b) { return a.time - b.time; });

  if (!lineData.length) {
    return;
  }

  // --- Collect close values for SMA ---
  var closeValues = [];
  for (var i = 0; i < lineData.length; i++) {
    closeValues.push(lineData[i].value);
  }

  // =====================================================
  // 2. Calculate 7-period Simple Moving Average
  // =====================================================

  // SMA periods: daily=20 bars (~1 month), 1W 10-min=20 bars (~3.3 hours), 1D minute=7
  var SMA_PERIOD = isDaily ? 20 : isMultiDay ? 20 : 7;

  function calculateSMA(closes, period) {
    var result = [];
    for (var i = 0; i < closes.length; i++) {
      if (i < period - 1) continue;
      var sum = 0;
      for (var j = i - period + 1; j <= i; j++) {
        sum += closes[j];
      }
      result.push({ time: lineData[i].time, value: sum / period });
    }
    return result;
  }

  var smaData = calculateSMA(closeValues, SMA_PERIOD);

  // =====================================================
  // 3. Create chart (English locale, ET display)
  // =====================================================

  var chart = LightweightCharts.createChart(container, {
    width:  container.clientWidth,
    height: container.clientHeight,
    layout: {
      background: { type: "solid", color: "#ffffff" },
      textColor: "#333333",
      fontSize: 12
    },
    grid: {
      vertLines: { color: "#f0f0f0" },
      horzLines: { color: "#f0f0f0" }
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal
    },
    rightPriceScale: {
      borderColor: "#d1d4dc"
    },
    timeScale: {
      borderColor: "#d1d4dc",
      timeVisible: !isDaily,
      secondsVisible: false,
      fixLeftEdge: true,
      fixRightEdge: true,
      tickMarkFormatter: function (time, tickMarkType, locale) {
        var d = new Date(time * 1000);
        if (isDaily) {
          return (d.getUTCMonth() + 1) + "/" + d.getUTCDate();
        }
        if (isMultiDay) {
          // Show date at day boundaries (first bar of a new trading day),
          // time for other ticks.  Lightweight Charts passes tickMarkType:
          //   0 = Year, 1 = Month, 2 = DayOfMonth, 3 = Time, 4 = TimeWithSeconds
          // Type 2 (DayOfMonth) fires at the first bar of each new date.
          if (tickMarkType <= 2) {
            return (d.getUTCMonth() + 1) + "/" + d.getUTCDate();
          }
          var h = d.getUTCHours();
          var m = d.getUTCMinutes();
          return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
        }
        var h = d.getUTCHours();
        var m = d.getUTCMinutes();
        return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
      }
    },
    localization: {
      locale: "en-US",
      dateFormat: "yyyy-MM-dd",
      timeFormatter: function (time) {
        var d = new Date(time * 1000);
        if (isDaily) {
          return (d.getUTCMonth() + 1) + "/" + d.getUTCDate() + "/" + d.getUTCFullYear();
        }
        if (isMultiDay) {
          // Tooltip: show full date + time
          return (d.getUTCMonth() + 1) + "/" + d.getUTCDate() + " " +
            (d.getUTCHours() < 10 ? "0" : "") + d.getUTCHours() + ":" +
            (d.getUTCMinutes() < 10 ? "0" : "") + d.getUTCMinutes();
        }
        var h = d.getUTCHours();
        var m = d.getUTCMinutes();
        return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
      }
    }
  });

  // --- Direction-based color for the main price line ---
  var firstClose = lineData[0].value;
  var lastClose  = lineData[lineData.length - 1].value;
  var isUp = lastClose >= firstClose;

  var LINE_COLOR_UP   = "#26a69a";   // teal-green
  var LINE_COLOR_DOWN = "#ef5350";   // red
  var FILL_COLOR_UP   = "rgba(38, 166, 154, 0.12)";
  var FILL_COLOR_DOWN = "rgba(239, 83, 80, 0.12)";

  var dirLineColor = isUp ? LINE_COLOR_UP : LINE_COLOR_DOWN;
  var dirFillColor = isUp ? FILL_COLOR_UP : FILL_COLOR_DOWN;

  // --- Primary price line ---
  var lineSeries = chart.addLineSeries({
    color: dirLineColor,
    lineWidth: 2,
    crosshairMarkerVisible: true,
    crosshairMarkerRadius: 4,
    priceLineVisible: true,
    priceLineColor: dirLineColor,
    lastValueVisible: true
  });
  lineSeries.setData(lineData);

  // --- Filled area under the price line ---
  var areaSeries = chart.addAreaSeries({
    topColor: dirFillColor,
    bottomColor: "rgba(0, 0, 0, 0)",
    lineColor: "rgba(0, 0, 0, 0)",
    lineWidth: 0,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false
  });
  areaSeries.setData(lineData);

  // --- SMA overlay (muted, behind the price line) ---
  var SMA_COLOR = "rgba(200, 160, 110, 0.50)";
  var smaSeries = chart.addLineSeries({
    color: SMA_COLOR,
    lineWidth: 1,
    lineStyle: 2,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false
  });
  smaSeries.setData(smaData);

  // =====================================================
  // 4. Legend (top-left, updates on crosshair move)
  // =====================================================

  var legend = document.createElement("div");
  legend.style.cssText =
    "position:absolute;top:8px;left:12px;z-index:10;" +
    "font:12px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;" +
    "color:#333;pointer-events:none;";
  container.appendChild(legend);

  function defaultLegend() {
    return '<span style="font-weight:700;font-size:13px;">' +
      (symbol || "Stock") + '</span>' +
      '<span style="color:#999;font-size:11px;margin-left:6px;">' +
      'Price & SMA(' + SMA_PERIOD + ') \u00b7 ET</span>';
  }

  var PRICE_LEGEND_COLOR = dirLineColor;

  function formatPrice(v) {
    return v == null ? "\u2014" : "$" + v.toFixed(2);
  }

  function formatTime(epochSec) {
    var d = new Date(epochSec * 1000);
    if (isDaily) {
      return (d.getUTCMonth() + 1) + "/" + d.getUTCDate() + "/" + d.getUTCFullYear();
    }
    var h = d.getUTCHours();
    var m = d.getUTCMinutes();
    var hhmm = (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
    if (isMultiDay) {
      return (d.getUTCMonth() + 1) + "/" + d.getUTCDate() + " " + hhmm;
    }
    return hhmm;
  }

  legend.innerHTML = defaultLegend();

  chart.subscribeCrosshairMove(function (param) {
    if (!param || !param.time) {
      legend.innerHTML = defaultLegend();
      return;
    }

    var price = param.seriesData.get(lineSeries);
    var sma   = param.seriesData.get(smaSeries);

    var parts = '<span style="font-weight:700;font-size:13px;">' +
      (symbol || "Stock") + "</span> ";
    parts += '<span style="color:#666;font-size:11px;">' +
      formatTime(param.time) + ' ET</span> ';
    if (price && price.value != null) {
      parts += ' <span style="color:' + PRICE_LEGEND_COLOR + ';font-weight:600;">' +
        formatPrice(price.value) + "</span>";
    }
    if (sma && sma.value != null) {
      parts += ' <span style="color:#b0906a;">SMA ' +
        formatPrice(sma.value) + "</span>";
    }
    legend.innerHTML = parts;
  });

  // =====================================================
  // 5. Set visible range to the user-selected window
  //
  // The selectedStart / selectedEnd strings are ET
  // wall-clock times ("yyyy-MM-dd HH:mm:ss").  We parse
  // them as UTC so the resulting epoch matches the chart
  // coordinate system (where UTC display == ET wall-clock).
  // If the user picked a wider range than the data covers,
  // the chart will honestly show the empty region instead
  // of silently shrinking.
  // =====================================================

  var rangeFrom = (typeof selectedStart !== "undefined") ? parseETDisplayString(selectedStart) : null;
  var rangeTo   = (typeof selectedEnd   !== "undefined") ? parseETDisplayString(selectedEnd)   : null;
  var hasRequestedIntradayRange = !isDaily && !isMultiDay && rangeFrom && rangeTo && rangeFrom < rangeTo;

  if (hasRequestedIntradayRange) {
    var viewportAnchorSeries = chart.addLineSeries({
      color: "rgba(0, 0, 0, 0)",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false
    });
    viewportAnchorSeries.setData([{ time: rangeFrom }, { time: rangeTo }]);
  }

  if (isDaily || isMultiDay) {
    chart.timeScale().fitContent();
  } else if (hasRequestedIntradayRange) {
    chart.timeScale().setVisibleRange({ from: rangeFrom, to: rangeTo });
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(function() {
        chart.timeScale().setVisibleRange({ from: rangeFrom, to: rangeTo });
      });
    }
  } else {
    chart.timeScale().fitContent();
  }

  // =====================================================
  // 6. Future-time region hint
  //
  //    When the visible range extends past the last data point
  //    (e.g. market still open, session end is 16:00 but data
  //    only goes to 14:35), shade the empty future region with
  //    a very faint overlay so it reads as "no data yet" rather
  //    than a rendering glitch.
  // =====================================================

  (function renderFutureHint() {
    if (isDaily || isMultiDay) return;
    if (lineData.length < 1 || !rangeTo) return;
    var lastDataTime = lineData[lineData.length - 1].time;
    // Only show the hint when there is a meaningful gap (> 2 min)
    if (rangeTo - lastDataTime < 120) return;

    var overlay = document.createElement("div");
    overlay.style.cssText =
      "position:absolute;top:0;bottom:22px;pointer-events:none;" +
      "background:repeating-linear-gradient(" +
      "135deg,transparent,transparent 6px,rgba(0,0,0,0.018) 6px,rgba(0,0,0,0.018) 7px);" +
      "z-index:1;border-left:1px dashed rgba(0,0,0,0.08);";
    container.appendChild(overlay);

    function positionOverlay() {
      var ts = chart.timeScale();
      var lastX = ts.timeToCoordinate(lastDataTime);
      var endX  = ts.timeToCoordinate(rangeTo);
      if (lastX == null || endX == null || endX <= lastX) {
        overlay.style.display = "none";
        return;
      }
      overlay.style.display = "block";
      overlay.style.left  = Math.round(lastX) + "px";
      overlay.style.width = Math.round(endX - lastX) + "px";
    }

    // Position on first render and on every scroll/zoom
    positionOverlay();
    chart.timeScale().subscribeVisibleTimeRangeChange(positionOverlay);
    window.addEventListener("resize", positionOverlay);
  })();

  // =====================================================
  // 7. Intraday summary bar
  //
  //    Computed from lineData (the deduplicated, sorted
  //    price series already used by the chart).
  //    Open  = first price in range
  //    Last  = last price in range
  //    High  = max price in range
  //    Low   = min price in range
  //    Change   = Last - Open
  //    Change % = (Last - Open) / Open * 100
  // =====================================================

  (function renderSummary() {
    var el = document.getElementById("intradaySummary");
    if (!el || lineData.length < 1) return;

    var openPrice  = lineData[0].value;
    var lastPrice  = lineData[lineData.length - 1].value;
    var highPrice  = openPrice;
    var lowPrice   = openPrice;
    for (var i = 1; i < lineData.length; i++) {
      var v = lineData[i].value;
      if (v > highPrice) highPrice = v;
      if (v < lowPrice)  lowPrice  = v;
    }

    var change    = lastPrice - openPrice;
    var changePct = openPrice !== 0 ? (change / openPrice) * 100 : 0;

    var sign      = change > 0 ? "+" : change < 0 ? "-" : "";
    var colorCls  = change > 0 ? "sum-pos" : change < 0 ? "sum-neg" : "sum-neutral";

    function fmt(v) { return "$" + v.toFixed(2); }

    function item(label, value, cls) {
      return '<span><span class="sum-label">' + label + '</span>' +
             '<span class="sum-value' + (cls ? " " + cls : "") + '">' + value + '</span></span>';
    }

    el.innerHTML =
      item("Open", fmt(openPrice)) +
      item("High", fmt(highPrice)) +
      item("Low",  fmt(lowPrice)) +
      item("Last", fmt(lastPrice)) +
      item("Change", sign + fmt(Math.abs(change)), colorCls) +
      item("Change %", sign + Math.abs(changePct).toFixed(2) + "%", colorCls);

    el.style.display = "flex";
  })();

  // =====================================================
  // 8. Volatility envelope toggle (Phase 2 MVP)
  //
  //    Adds two dashed line series for vol_band_low and
  //    vol_band_high when the user enables the toggle on
  //    daily-range charts (3M/6M/YTD/1Y).  For intraday or
  //    multi-day-sampled views, the toggle stays disabled
  //    because as_of_date is one row per trading day and
  //    cannot be aligned to minute-bar timestamps.
  //
  //    /api/volatility/history is fetched lazily on first
  //    enable and cached for subsequent toggles within the
  //    same page lifetime.
  // =====================================================

  (function setupVolatilityEnvelope() {
    var toggleBtn = document.getElementById("volEnvelopeToggle");
    if (!toggleBtn) {
      return;
    }

    if (!isDaily) {
      toggleBtn.disabled = true;
      toggleBtn.title = "Available on daily ranges (3M / 6M / YTD / 1Y)";
      return;
    }

    if (typeof symbol !== "string" || !symbol) {
      toggleBtn.disabled = true;
      return;
    }

    toggleBtn.disabled = false;

    var lowSeries = null;
    var highSeries = null;
    var cachedSeries = null; // [{time, low, high}, ...]
    var enabled = false;

    function dateStringToEpochSec(dateStr) {
      // Parse "yyyy-MM-dd" as midnight UTC so the value matches
      // the daily chart's coordinate system (epoch seconds at
      // midnight UTC, set in the data-loading section above).
      if (typeof dateStr !== "string" || dateStr.length < 10) {
        return null;
      }
      var parts = dateStr.slice(0, 10).split("-");
      if (parts.length !== 3) {
        return null;
      }
      var y = parseInt(parts[0], 10);
      var m = parseInt(parts[1], 10);
      var d = parseInt(parts[2], 10);
      if (isNaN(y) || isNaN(m) || isNaN(d)) {
        return null;
      }
      return Math.floor(Date.UTC(y, m - 1, d) / 1000);
    }

    function buildSeriesData(series) {
      var lowData = [];
      var highData = [];
      for (var i = 0; i < series.length; i++) {
        var item = series[i];
        if (item.volBandLow == null || item.volBandHigh == null) {
          continue;
        }
        var t = dateStringToEpochSec(item.asOfDate);
        if (t == null) { continue; }
        lowData.push({ time: t, value: Number(item.volBandLow) });
        highData.push({ time: t, value: Number(item.volBandHigh) });
      }
      return { low: lowData, high: highData };
    }

    function drawEnvelope() {
      if (!cachedSeries || !cachedSeries.length) {
        return;
      }
      var built = buildSeriesData(cachedSeries);
      if (!built.low.length) {
        return;
      }
      var BAND_COLOR = "rgba(120, 130, 145, 0.55)";
      lowSeries = chart.addLineSeries({
        color: BAND_COLOR,
        lineWidth: 1,
        lineStyle: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false
      });
      highSeries = chart.addLineSeries({
        color: BAND_COLOR,
        lineWidth: 1,
        lineStyle: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false
      });
      lowSeries.setData(built.low);
      highSeries.setData(built.high);
    }

    function clearEnvelope() {
      if (lowSeries) {
        try { chart.removeSeries(lowSeries); } catch (e) { /* ignore */ }
        lowSeries = null;
      }
      if (highSeries) {
        try { chart.removeSeries(highSeries); } catch (e) { /* ignore */ }
        highSeries = null;
      }
    }

    function setButtonLabel() {
      toggleBtn.textContent = enabled
        ? "Hide volatility envelope"
        : "Show volatility envelope";
    }

    toggleBtn.addEventListener("click", function() {
      if (enabled) {
        clearEnvelope();
        enabled = false;
        setButtonLabel();
        return;
      }

      if (cachedSeries) {
        drawEnvelope();
        enabled = true;
        setButtonLabel();
        return;
      }

      toggleBtn.disabled = true;
      toggleBtn.textContent = "Loading…";

      fetch("/api/volatility/history?symbol=" + encodeURIComponent(symbol) + "&days=300")
        .then(function(resp) {
          if (!resp.ok) {
            throw new Error("history fetch failed");
          }
          return resp.json();
        })
        .then(function(data) {
          var series = (data && data.series) ? data.series : [];
          cachedSeries = series;
          if (!series.length) {
            toggleBtn.disabled = true;
            toggleBtn.textContent = "No envelope data";
            return;
          }
          drawEnvelope();
          enabled = true;
          toggleBtn.disabled = false;
          setButtonLabel();
        })
        .catch(function() {
          toggleBtn.disabled = false;
          enabled = false;
          setButtonLabel();
          console.warn("Volatility envelope: history fetch failed");
        });
    });
  })();

  window.addEventListener("resize", function () {
    chart.applyOptions({ width: container.clientWidth });
  });
});
