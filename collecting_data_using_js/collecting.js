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

const con = mysql.createConnection({
  host: "127.0.0.1",
  user: "root",
  password: "root",
  database: "stock"
});

function myfunction(position) {

  const url = "https://api.twelvedata.com/time_series?symbol=" + symbolList[position] + "&interval=1min&outputsize=390&apikey=" + process.env.TWELVE;
  //console.log("check point" + position);
  //console.log(url);
  //console.log("check");
  https.get(url, function(response) {
    //console.log(response);

    let rawData = '';
    response.on('data', (chunk) => {
      rawData += chunk;
    });
    response.on('end', () => {
      try {
        const parsedData = JSON.parse(rawData);
        //console.log(parsedData.values);
        //console.log("this is test" + parsedData.fifty_two_week.low);
        // get all the values
        let nameForTable = symbolList[position].replace(".", '');
        if (nameForTable == "NOW") {
          nameForTable = "NOW1"
        }
        if (nameForTable == "ALL") {
          nameForTable = "ALL1"
        }
        if (nameForTable == "KEYS") {
          nameForTable = "KEYS1"
        }
        if (nameForTable == "KEY") {
          nameForTable = "KEY1"
        }
        const creatTable = "CREATE TABLE IF NOT EXISTS "+ nameForTable+"( id INT NOT NULL AUTO_INCREMENT, timePoint DATETIME,minuteOpen INT,minuteHigh INT,minuteLow INT,minuteClose INT,minuteVolume INT,PRIMARY KEY(id));"
        //console.log(creatTable)
        con.query(creatTable, function(err, result) {
          if (err) throw err;
          console.log("Table " + symbolList[position] +" created!");
        })
        for (var i = 0; i < 390; i++) {
          const date = parsedData.values[i].datetime;
          const open = parsedData.values[i].open;
          const high = parsedData.values[i].high;
          const low = parsedData.values[i].low;
          const close = parsedData.values[i].close;
          const volume = parsedData.values[i].volume;



          const saveValue = "INSERT INTO "+nameForTable+" VALUES(default,'" + date + "','" + open + "','" + high + "','" + low + "','" + close +
            "','" + volume + "')"
          //console.log(saveValue);
          con.query(saveValue, function(err, result) {
            if (err) throw err;
            //console.log("inserted!");
          })


        }
        // const date = parsedData.values[1].datetime;
        // const open = parsedData.values[1].open;
        // const high = parsedData.values[1].high;
        // const low = parsedData.values[1].low;
        // const close = parsedData.values[1].close;
        // const volume = parsedData.values[1].volume;
        //
        //
        //
        // const saveValue = "INSERT INTO AAPL VALUES(default,'" + date + "','" + open + "','" + high + "','" + low + "','" + close +
        //   "','" + volume + "')"
        // console.log(saveValue);
        //console.log(symbolList[0]);
        //symbolList.forEach(element => console.log(element));


        // con.query(saveValue, function(err, result) {
        //   if (err) throw err;
        //   console.log("inserted!");
        // })
        console.log("390 rows of the data has been stored.")
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
  return position;
}


app.listen(3000,function() {
  console.log("Data collection process started. This process will create table if not exists and store new data into that table. The process runs every nine seconds and will stop at 100. The data is the every minute of that stock on current day.");
  //console.log(myfunction(2));
  let test = 349;
  cron.schedule('*/9 * * * * *', () => {
    //console.log('Hello World');
    //console.log("check");
    if (test < 500) {
      console.log(myfunction(test++));
    } else {
      console.log("finished, current status:" + test);
    }



    // let url1 = "https://api.twelvedata.com/quote?symbol=" + symbolList[i] + "&apikey=" + process.env.TWELVE;
    // console.log("check");
    // console.log(url1);
  });

})
