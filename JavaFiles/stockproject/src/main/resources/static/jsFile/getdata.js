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
  // Lightweight Charts renders timestamps as UTC.
  // The backend stores ET wall-clock times in the DB and
  // sends epoch millis produced by java.sql.Timestamp
  // .getTime(), which interprets the DB value in the
  // JVM's system timezone.  Since the browser runs on
  // the same machine, its local timezone matches the JVM.
  //
  // To recover the original DB wall-clock value (ET) we
  // extract the browser-local hours/minutes/seconds and
  // pack them into a fake-UTC epoch.  This makes the
  // x-axis read the same values shown in the page header
  // (which are also formatted in JVM-local time by
  // SimpleDateFormat).
  // =====================================================

  function toDisplaySeconds(epochMs) {
    var d = new Date(epochMs);
    return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(),
                    d.getHours(), d.getMinutes(), d.getSeconds()) / 1000;
  }

  // =====================================================
  // 1. Transform backend data into Lightweight Charts format
  //
  //    Backend provides (via Thymeleaf):
  //      apple[i]     = [open, high, low, close]
  //      timepoint[i] = epoch millis (JVM-local interpretation of DB timestamps)
  //
  //    The backend stores OHLC columns per minute bar, but
  //    in practice the source data provides a single price
  //    per timestamp (open == high == low == close).
  //    We use a line series keyed on the close price.
  // =====================================================

  var rawData = [];

  for (var i = 0; i < timepoint.length; i++) {
    // Daily data: timestamps are already midnight UTC — use directly.
    // Intraday: convert JVM-local millis to fake-UTC display seconds.
    var displaySec = isDaily
        ? Math.floor(timepoint[i] / 1000)
        : toDisplaySeconds(timepoint[i]);
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

  // --- Diagnostic logging ---
  console.log("Chart data: " + rawData.length + " raw, " +
              lineData.length + " after dedup");
  console.log("First 5:", lineData.slice(0, 5));
  console.log("Last 5:",  lineData.slice(-5));

  // --- Collect close values for SMA ---
  var closeValues = [];
  for (var i = 0; i < lineData.length; i++) {
    closeValues.push(lineData[i].value);
  }

  // =====================================================
  // 2. Calculate 7-period Simple Moving Average
  // =====================================================

  var isDaily = (typeof dataGranularity !== "undefined" && dataGranularity === "daily");
  var isMultiDay = (typeof dataGranularity !== "undefined" && dataGranularity === "30min");
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
  console.log("SMA data points: " + smaData.length);

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

  // --- Primary price line ---
  var lineSeries = chart.addLineSeries({
    color: "#2962FF",
    lineWidth: 2,
    crosshairMarkerVisible: true,
    crosshairMarkerRadius: 4,
    priceLineVisible: true,
    lastValueVisible: true
  });
  lineSeries.setData(lineData);

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
      parts += ' <span style="color:#2962FF;font-weight:600;">' +
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

  function parseETDisplayString(str) {
    if (!str) return null;
    var p = str.split(/[- :]/);
    if (p.length < 5) return null;
    return Date.UTC(
      parseInt(p[0], 10),
      parseInt(p[1], 10) - 1,
      parseInt(p[2], 10),
      parseInt(p[3], 10),
      parseInt(p[4], 10),
      p[5] ? parseInt(p[5], 10) : 0
    ) / 1000;
  }

  var rangeFrom = (typeof selectedStart !== "undefined") ? parseETDisplayString(selectedStart) : null;
  var rangeTo   = (typeof selectedEnd   !== "undefined") ? parseETDisplayString(selectedEnd)   : null;

  if (isDaily || isMultiDay) {
    chart.timeScale().fitContent();
  } else if (rangeFrom && rangeTo && rangeFrom < rangeTo) {
    chart.timeScale().setVisibleRange({ from: rangeFrom, to: rangeTo });
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

  window.addEventListener("resize", function () {
    chart.applyOptions({ width: container.clientWidth });
  });
});
