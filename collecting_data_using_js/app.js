require('dotenv').config();

const express = require("express");
const https = require("https");
const bodyParser = require("body-parser");
const ejs = require("ejs");
const app = express();
const cron = require("node-cron");

const mysql = require("mysql");
app.set('view engine', 'ejs');

const symbolList = ["AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "TSLA", "BRK.B", "JNJ", "UNH", "FB", "NVDA", "XOM", "JPM", "PG", "V", "CVX", "HD", "MA", "PFE", "ABBV", "BAC", "KO", "MRK", "LLY", "AVGO", "PEP", "TMO", "VZ", "ABT", "CMCSA", "DIS", "COST", "ADBE", "CSCO", "ACN", "MCD", "INTC", "WMT", "BMY", "WFC", "LIN", "DHR", "AMD", "PM", "TXN", "CRM", "QCOM", "T", "NEE", "MDT", "UNP", "AMGN", "COP", "NKE", "RTX", "HON", "LOW", "CVS", "UPS", "SPGI", "IBM", "ANTM", "MS", "CAT", "AMT", "ORCL", "GS", "LMT", "INTU", "DE", "C", "AMAT", "AXP", "PYPL", "SCHW", "MO", "PLD", "CB", "ADP", "BKNG", "NOW", "MDLZ", "ADI", "BLK", "MMM", "DUK", "GE", "CI", "SBUX", "NFLX", "GILD", "ISRG", "SO", "MU", "SYK", "CCI", "MMC", "ZTS", "TMUS", "TGT", "TJX", "BDX", "EOG", "REGN", "BA", "CSX", "CME", "D", "USB", "LRCX", "NOC", "PNC", "VRTX", "PGR", "CL", "SHW", "TFC", "ATVI", "PXD", "FIS", "EW", "WM", "ITW", "SLB", "AON", "EQIX", "CHTR", "OXY", "FISV", "BSX", "MPC", "HUM", "EL", "NSC", "ETN", "ICE", "FCX", "NEM", "GM", "SRE", "APD", "KLAC", "DOW", "VLO", "F", "MRNA", "GD", "AEP", "EMR", "HCA", "FDX", "CNC", "AIG", "MCK", "PSA", "COF", "DG", "NXPI", "ADM", "EXC", "SNPS", "MCO", "LHX", "PSX", "MET", "DVN", "ROP", "KMB", "CTVA", "MAR", "ADSK", "WMB", "TRV", "ORLY", "SYY", "APH", "XEL", "TEL", "GIS", "CDNS", "ECL", "AZO", "HPQ", "WBD", "IQV", "STZ", "WELL", "O", "ILMN", "PRU", "FTNT", "PAYX", "KMI", "A", "CTSH", "EA", "HLT", "MCHP", "JCI", "DLR", "BAX", "SPG", "CMG", "MSI", "ALL", "SBAC", "GPN", "PEG", "PH", "ED", "AFL", "MSCI", "DD", "ROST", "NUE", "IFF", "MNST", "HAL", "AJG", "WEC", "KR", "BK", "CARR", "YUM", "BKR", "CTAS", "HES", "IDXX", "OTIS", "ES", "TT", "DXCM", "DLTR", "DFS", "HSY", "TWTR", "FAST", "MTB", "WBA", "PPG", "RMD", "CMI", "LYB", "TDG", "BIIB", "WY", "AMP", "PCAR", "OKE", "MTD", "EBAY", "ALB", "AVB", "CERN", "TROW", "KHC", "VRSK", "AME", "CBRE", "RSG", "AWK", "FRC", "LUV", "APTV", "SIVB", "KEYS", "GLW", "DAL", "EIX", "EQR", "DTE", "TSN", "CTRA", "WTW", "ZBH", "FITB", "STT", "FE", "AEE", "CPRT", "EFX", "ETR", "ROK", "ARE", "LH", "BALL", "ANET", "EXR", "MOS", "HIG", "ABC", "STE", "VTR", "ODFL", "WST", "ENPH", "MKC", "PPL", "FANG", "CDW", "DHI", "CF", "ANSS", "CHD", "MTCH", "VMC", "NTRS", "MRO", "TSCO", "FTV", "IT", "GWW", "MLM", "ALGN", "CMS", "MAA", "WAT", "AMCR", "HOLX", "URI", "HPE", "DRE", "PARA", "CNP", "ULTA", "RF", "EXPE", "LEN", "HBAN", "GPC", "SWK", "CFG", "IP", "CEG", "DOV", "EPAM", "CINF", "FLT", "ESS", "TDY", "WDC", "MOH", "PKI", "MPWR", "IR", "CTLT", "EXPD", "J", "ZBRA", "K", "KEY", "SYF", "PFG", "RJF", "CLX", "DGX", "SWKS", "TER", "COO", "NDAQ", "STX", "WAB", "CE", "TRMB", "PWR", "AKAM", "BR", "BBY", "VRSN", "POOL", "PEAK", "OMC", "CAH", "FMC", "NTAP", "EVRG", "CAG", "GRMN", "ATO", "DRI", "BXP", "APA", "KMX", "XYL", "LNT", "VFC", "PKG", "CPT", "LDOS", "TECH", "UAL", "VTRS", "IRM", "GNRC", "INCY", "KIM", "WRB", "IEX", "TYL", "AVY", "TTWO", "UDR", "TXT", "HST", "NLOK", "AES", "SJM", "FDS", "NVR", "HRL", "JBHT", "LKQ", "TFX", "EMN", "CHRW", "SEDG", "JKHY", "MAS", "PAYC", "RCL", "HWM", "BRO", "MGM", "DPZ", "L", "CTXS", "LYV", "AAP", "IPG", "WRK", "SBNY", "NI", "CRL", "SNA", "PTC", "HSIC", "LVS", "QRVO", "NRG", "BF.B", "CBOE", "BIO", "NDSN", "HAS", "RE", "CCL", "AAL", "ABMD", "FOXA", "PHM", "BBWI", "LUMN", "CZR", "WHR", "AIZ", "MKTX", "ETSY", "RHI", "REG", "ALLE", "CMA", "TAP", "CPB", "JNPR", "BWA", "FFIV", "OGN", "NLSN", "FBHS", "LW", "SEE", "LNC", "GL", "UHS", "PNW", "TPR", "XRAY", "HII", "PNR", "ZION", "MHK", "FRT", "AOS", "ROL", "CDAY", "NWL", "DXC", "BEN", "NWSA", "NCLH", "WYNN", "IVZ", "ALK", "DVA", "VNO", "DISH", "PENN", "PVH", "FOX", "RL", "IPGP", "NWS", "UAA", "UA", "EMBC"];

app.use(bodyParser.urlencoded({
  extended: true
}));
app.use(express.static("public"));


const con = mysql.createConnection({
  host: "127.0.0.1",
  user: "root",
  password: "root",
  database: "stock"
});
let test = 220;
cron.schedule('*/9 * * * * *', () => {
  console.log('Hello World');
  console.log("check");
  if (test < 500) {
    console.log(myfunction(test++));
  } else {
    console.log("finished, current status:" + test);
  }


  main();
  // let url1 = "https://api.twelvedata.com/quote?symbol=" + symbolList[i] + "&apikey=" + process.env.TWELVE;
  // console.log("check");
  // console.log(url1);
});


function myfunction(position) {

  const url1 = "https://api.twelvedata.com/quote?symbol=" + symbolList[position] + "&apikey=" + process.env.TWELVE;
  //console.log("check point" + position);
  console.log(url1);
  //console.log("check");
  https.get(url1, function(response) {
    //console.log(response);

    let rawData = '';
    response.on('data', (chunk) => {
      rawData += chunk;
    });
    response.on('end', () => {
      try {
        const parsedData = JSON.parse(rawData);
        //console.log(parsedData);
        //console.log("this is test" + parsedData.fifty_two_week.low);
        // get all the values
        const symbol = parsedData.symbol;
        let name = parsedData.name;
        name = name.replace("'", ',');
        //console.log("herehehhrehrherhhehrhhehreh" + name.replace("'", ','));
        const exchange = parsedData.exchange;
        //const mic_code = parsedData.mic_code;
        const currency = parsedData.currency;
        const datetime = parsedData.datetime;
        const timestamp = parsedData.timestamp;
        const open = parsedData.open;
        const high = parsedData.high;
        const low = parsedData.low;
        const close = parsedData.close;
        const volume = parsedData.volume;
        const previous_close = parsedData.previous_close;
        const change = parsedData.change;
        const percent_change = parsedData.percent_change;
        const average_volume = parsedData.average_volume;
        const rolling_1d_change = parsedData.rolling_1d_change;
        const rolling_7d_change = parsedData.rolling_7d_change;
        const rolling_period_change = parsedData.rolling_period_change;



        const is_market_open = parsedData.is_market_open;
        const fifty_two_weeklow = parsedData.fifty_two_week.low;
        const fifty_two_weekhigh = parsedData.fifty_two_week.high;
        const fifty_two_weeklow_change = parsedData.fifty_two_week.low_change;
        const fifty_two_weekhigh_change = parsedData.fifty_two_week.high_change;
        const fifty_two_weeklow_change_percent = parsedData.fifty_two_week.low_change_percent;

        const fifty_two_weekhigh_change_percent = parsedData.fifty_two_week.high_change_percent;
        const fifty_two_weekrange = parsedData.fifty_two_week.range;

        const saveValue = "INSERT INTO everydayAfterClose VALUES(default,'" + symbol + "','" + name + "','" + exchange + "','" + currency + "','" + datetime +
          "','" + timestamp + "','" + open + "','" + high + "','" + low + "','" + close + "','" + volume + "','" + previous_close + "','" + change + "','" + percent_change +
          "','" + average_volume + "','" + is_market_open + "','" + fifty_two_weeklow + "','" + fifty_two_weekhigh + "','" + fifty_two_weeklow_change + "','" +
          fifty_two_weekhigh_change + "','" + fifty_two_weeklow_change_percent + "','" + fifty_two_weekhigh_change_percent + "','" + fifty_two_weekrange + "')"
        //console.log(saveValue);
        //console.log(symbolList[0]);
        //symbolList.forEach(element => console.log(element));
        con.query(saveValue, function(err, result) {
          if (err) throw err;
          console.log("inserted!");
        })
      } catch (e) {
        console.error(e.message);
      }
    });
    // response.on("data", function(data) {
    //   //console.log(data);
    // //  const stock = JSON.parse(data);
    //   //const info = stock.values;
    //
    // })

  })
  return test;
}
app.get("/", function(req, res) {
  let position = 0;
  cron.schedule('*/8 * * * * *', () => {
    //console.log('Hello World');
    const url1 = "https://api.twelvedata.com/quote?symbol=" + symbolList[i] + "&apikey=" + process.env.TWELVE;
    console.log(url1);
    console.log("check");
    https.get(url1, function(response) {
      //console.log(response);

      let rawData = '';
      response.on('data', (chunk) => {
        rawData += chunk;
      });
      response.on('end', () => {
        try {
          const parsedData = JSON.parse(rawData);
          //console.log(parsedData);
          //console.log("this is test" + parsedData.fifty_two_week.low);
          // get all the values
          const symbol = parsedData.symbol;
          const name = parsedData.name;
          const exchange = parsedData.exchange;
          //const mic_code = parsedData.mic_code;
          const currency = parsedData.currency;
          const datetime = parsedData.datetime;
          const timestamp = parsedData.timestamp;
          const open = parsedData.open;
          const high = parsedData.high;
          const low = parsedData.low;
          const close = parsedData.close;
          const volume = parsedData.volume;
          const previous_close = parsedData.previous_close;
          const change = parsedData.change;
          const percent_change = parsedData.percent_change;
          const average_volume = parsedData.average_volume;
          const rolling_1d_change = parsedData.rolling_1d_change;
          const rolling_7d_change = parsedData.rolling_7d_change;
          const rolling_period_change = parsedData.rolling_period_change;



          const is_market_open = parsedData.is_market_open;
          const fifty_two_weeklow = parsedData.fifty_two_week.low;
          const fifty_two_weekhigh = parsedData.fifty_two_week.high;
          const fifty_two_weeklow_change = parsedData.fifty_two_week.low_change;
          const fifty_two_weekhigh_change = parsedData.fifty_two_week.high_change;
          const fifty_two_weeklow_change_percent = parsedData.fifty_two_week.low_change_percent;

          const fifty_two_weekhigh_change_percent = parsedData.fifty_two_week.high_change_percent;
          const fifty_two_weekrange = parsedData.fifty_two_week.range;

          const saveValue = "INSERT INTO everydayAfterClose VALUES(default,'" + symbol + "','" + name + "','" + exchange + "','" + currency + "','" + datetime +
            "','" + timestamp + "','" + open + "','" + high + "','" + low + "','" + close + "','" + volume + "','" + previous_close + "','" + change + "','" + percent_change +
            "','" + average_volume + "','" + is_market_open + "','" + fifty_two_weeklow + "','" + fifty_two_weekhigh + "','" + fifty_two_weeklow_change + "','" +
            fifty_two_weekhigh_change + "','" + fifty_two_weeklow_change_percent + "','" + fifty_two_weekhigh_change_percent + "','" + fifty_two_weekrange + "')"
          //console.log(saveValue);
          //console.log(symbolList[0]);
          //symbolList.forEach(element => console.log(element));
          con.query(saveValue, function(err, result) {
            if (err) throw err;
            console.log("inserted!");
          })
        } catch (e) {
          console.error(e.message);
        }
      });
      // response.on("data", function(data) {
      //   //console.log(data);
      // //  const stock = JSON.parse(data);
      //   //const info = stock.values;
      //
      // })

    })
  });
  const url = "https://api.twelvedata.com/time_series?symbol=GOOGL&interval=15min&apikey=" + process.env.TWELVE;
  const url1 = "https://api.twelvedata.com/quote?symbol=GOOGL&apikey=" + process.env.TWELVE;
  //console.log(url);
  function timer(ms) {
    return new Promise(res => setTimeout(res, ms));
  }
  //console.log(process.env.APP_ID)
  async function task(i) { // 3
    await timer(8000);
    console.log(`Task ${i} done!` + symbolList[i]);
  }

  async function main() {
    for (let i = 0; i < 500; i += 10) {
      const url1 = "https://api.twelvedata.com/quote?symbol=" + symbolList[i] + "&apikey=" + process.env.TWELVE;
      console.log(url1);
      https.get(url1, function(response) {
        //console.log(response);

        let rawData = '';
        response.on('data', (chunk) => {
          rawData += chunk;
        });
        response.on('end', () => {
          try {
            const parsedData = JSON.parse(rawData);
            //console.log(parsedData);
            //console.log("this is test" + parsedData.fifty_two_week.low);
            // get all the values
            const symbol = parsedData.symbol;
            const name = parsedData.name;
            const exchange = parsedData.exchange;
            //const mic_code = parsedData.mic_code;
            const currency = parsedData.currency;
            const datetime = parsedData.datetime;
            const timestamp = parsedData.timestamp;
            const open = parsedData.open;
            const high = parsedData.high;
            const low = parsedData.low;
            const close = parsedData.close;
            const volume = parsedData.volume;
            const previous_close = parsedData.previous_close;
            const change = parsedData.change;
            const percent_change = parsedData.percent_change;
            const average_volume = parsedData.average_volume;
            const rolling_1d_change = parsedData.rolling_1d_change;
            const rolling_7d_change = parsedData.rolling_7d_change;
            const rolling_period_change = parsedData.rolling_period_change;



            const is_market_open = parsedData.is_market_open;
            const fifty_two_weeklow = parsedData.fifty_two_week.low;
            const fifty_two_weekhigh = parsedData.fifty_two_week.high;
            const fifty_two_weeklow_change = parsedData.fifty_two_week.low_change;
            const fifty_two_weekhigh_change = parsedData.fifty_two_week.high_change;
            const fifty_two_weeklow_change_percent = parsedData.fifty_two_week.low_change_percent;

            const fifty_two_weekhigh_change_percent = parsedData.fifty_two_week.high_change_percent;
            const fifty_two_weekrange = parsedData.fifty_two_week.range;

            const saveValue = "INSERT INTO everydayAfterClose VALUES(default,'" + symbol + "','" + name + "','" + exchange + "','" + currency + "','" + datetime +
              "','" + timestamp + "','" + open + "','" + high + "','" + low + "','" + close + "','" + volume + "','" + previous_close + "','" + change + "','" + percent_change +
              "','" + average_volume + "','" + is_market_open + "','" + fifty_two_weeklow + "','" + fifty_two_weekhigh + "','" + fifty_two_weeklow_change + "','" +
              fifty_two_weekhigh_change + "','" + fifty_two_weeklow_change_percent + "','" + fifty_two_weekhigh_change_percent + "','" + fifty_two_weekrange + "')"
            //console.log(saveValue);
            //console.log(symbolList[0]);
            //symbolList.forEach(element => console.log(element));
            con.query(saveValue, function(err, result) {
              if (err) throw err;
              console.log("inserted!");
            })
          } catch (e) {
            console.error(e.message);
          }
        });
        // response.on("data", function(data) {
        //   //console.log(data);
        // //  const stock = JSON.parse(data);
        //   //const info = stock.values;
        //
        // })

      })




      await task(i);


    }
  }
  // https.get(url1, function(response) {
  //   //console.log(response);
  //
  //   let rawData = '';
  //   response.on('data', (chunk) => {
  //     rawData += chunk;
  //   });
  //   response.on('end', () => {
  //     try {
  //       const parsedData = JSON.parse(rawData);
  //       //console.log(parsedData);
  //       //console.log("this is test" + parsedData.fifty_two_week.low);
  //       // get all the values
  //       const symbol = parsedData.symbol;
  //       const name = parsedData.name;
  //       const exchange = parsedData.exchange;
  //       //const mic_code = parsedData.mic_code;
  //       const currency = parsedData.currency;
  //       const datetime = parsedData.datetime;
  //       const timestamp = parsedData.timestamp;
  //       const open = parsedData.open;
  //       const high = parsedData.high;
  //       const low = parsedData.low;
  //       const close = parsedData.close;
  //       const volume = parsedData.volume;
  //       const previous_close = parsedData.previous_close;
  //       const change = parsedData.change;
  //       const percent_change = parsedData.percent_change;
  //       const average_volume = parsedData.average_volume;
  //       const rolling_1d_change = parsedData.rolling_1d_change;
  //       const rolling_7d_change = parsedData.rolling_7d_change;
  //       const rolling_period_change = parsedData.rolling_period_change;
  //
  //
  //
  //       const is_market_open = parsedData.is_market_open;
  //       const fifty_two_weeklow = parsedData.fifty_two_week.low;
  //       const fifty_two_weekhigh = parsedData.fifty_two_week.high;
  //       const fifty_two_weeklow_change = parsedData.fifty_two_week.low_change;
  //       const fifty_two_weekhigh_change = parsedData.fifty_two_week.high_change;
  //       const fifty_two_weeklow_change_percent = parsedData.fifty_two_week.low_change_percent;
  //
  //       const fifty_two_weekhigh_change_percent = parsedData.fifty_two_week.high_change_percent;
  //       const fifty_two_weekrange = parsedData.fifty_two_week.range;
  //
  //       const saveValue = "INSERT INTO everydayAfterClose VALUES(default,'" + symbol + "','" + name + "','" + exchange + "','" + currency + "','" + datetime +
  //         "','" + timestamp + "','" + open + "','" + high + "','" + low + "','" + close + "','" + volume + "','" + previous_close + "','" + change + "','" + percent_change +
  //         "','" + average_volume + "','" + is_market_open + "','" + fifty_two_weeklow + "','" + fifty_two_weekhigh + "','" + fifty_two_weeklow_change + "','" +
  //         fifty_two_weekhigh_change + "','" + fifty_two_weeklow_change_percent + "','" + fifty_two_weekhigh_change_percent + "','" + fifty_two_weekrange + "')"
  //       console.log(saveValue);
  //       console.log(symbolList[0]);
  //
  //       con.query(saveValue, function(err, result) {
  //         if (err) throw err;
  //         console.log("inserted!");
  //       })
  //     } catch (e) {
  //       console.error(e.message);
  //     }
  //   });
  // response.on("data", function(data) {
  //   //console.log(data);
  // //  const stock = JSON.parse(data);
  //   //const info = stock.values;
  //
  // })

  //})
  //main();

  con.query("select * from everydayAfterClose", function(err, result) {
    if (err) throw err;
    //console.log(result);
    //console.log("result");
  });
  res.send("done");
})
//https://api.twelvedata.com/quote?symbol=AAPL&apikey=your_api_key
app.listen(3000, function() {
  console.log("started");
})
//
// const symbol = parsedData.symbol;
// const name = parsedData.name;
// const exchange = parsedData.exchange;
// const mic_code = parsedData.mic_code;
// const currency= parsedData.currency;
// const datetime= parsedData.datetime;
// const timestamp= parsedData.timestamp;
// const open= parsedData.open;
// const high= parsedData.high;
// const low= parsedData.low;
// const close = parsedData.close;
// const volume= parsedData.volume;
// const previous_close= parsedData.previous_close;
// const change= parsedData.change;
// const percent_change= parsedData.percent_change;
//
//
//
// const average_volume= parsedData.average_volume;
// const is_market_open = parsedData.is_market_open;
// const fifty_two_weeklow= parsedData.fifty_two_week.low;
// const fifty_two_weekhigh= parsedData.fifty_two_week.high;
// const fifty_two_weeklow_change= parsedData.fifty_two_week.low_change;
// const fifty_two_weekhigh_change_percent= parsedData.fifty_two_week.high_change_percent;
// const fifty_two_weekrange= parsedData.fifty_two_week.range;
