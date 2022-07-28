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
  // host: "stockproject.c41k9xcwi5rs.us-east-1.rds.amazonaws.com",
  // user: "insert",
  // password: "harryzhao",
  // database: "stock"
  host: "127.0.0.1",
  user: "root",
  password: "root",
  database: "stock"
});

function myfunction(position, startingMonth, startingDay, endMonth, endDay, startYear, endYear) {



  let datetime = "&start_date="+startYear+"-"+ startingMonth+"-"+startingDay+  " 09:30:00&end_date="+endYear+"-"+ endMonth+"-"+ endDay+" 15:59:00&" ;
  // const url = "https://api.twelvedata.com/time_series?symbol=" + symbolList[position] + "&interval=1min&outputsize=390&apikey=" + process.env.TWELVE;
  const url = "https://api.twelvedata.com/time_series?symbol="+symbolList[position]+"&interval=1min"+ datetime+"apikey=" + process.env.TWELVE;

  //console.log("check point" + position);
  console.log("Check point: the url is: " + url);
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
        const creatTable = "CREATE TABLE IF NOT EXISTS time_series ( company_name varchar(10), time_point DATETIME, minute_open double, minute_high double, minute_low double, minute_close double, minute_volume int,PRIMARY KEY(company_name, time_point));"
        console.log(creatTable)
        con.query(creatTable, function(err, result) {
          if (err) throw err;
          //console.log("Table " + symbolList[position] +" created!");
        })

        //console.log("The length of the json is " + Object.keys(parsedData.values).length);
        let lengthOfJson = Object.keys(parsedData.values).length;
        for (var i = 0; i < lengthOfJson; i++) {
          const date = parsedData.values[i].datetime;
          const open = parsedData.values[i].open;
          const high = parsedData.values[i].high;
          const low = parsedData.values[i].low;
          const close = parsedData.values[i].close;
          const volume = parsedData.values[i].volume;



          const saveValue = "INSERT INTO time_series VALUES('"+symbolList[position]+"','" + date + "','" + open + "','" + high + "','" + low + "','" + close +
            "','" + volume + "')";
          //console.log(saveValue);
          con.query(saveValue, function(err, result) {
            if (err) {
              console.log(err);
            }
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
        console.log(lengthOfJson + " rows of the data has been stored.")
      } catch (e) {
        //console.error(e.message);
        console.log("error");
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


// app.listen(3000,function() {
//   console.log("Data collection process started. This process will create table if not exists and store new data into that table. The process runs every nine seconds and will stop at 100. The data is the every minute of that stock on current day.");
//   //console.log(myfunction(2));
//   let test = 0;
//   cron.schedule('*/20 * * * * *', () => {
//     //console.log('Hello World');
//     //console.log("check");
//
//     if (test < 500) {
//       console.log(myfunction(test++));
//     } else {
//       console.log("finished, current status:" + test);
//     }
//
//
//
//     // let url1 = "https://api.twelvedata.com/quote?symbol=" + symbolList[i] + "&apikey=" + process.env.TWELVE;
//     // console.log("check");
//      console.log(url1);
//   });
//
// })

// app.listen(3000,function() {
//     cron.schedule('*/1 * * * * *', () => {
//       //console.log('Hello World');
//       //console.log("check");
//     let startDay = 20;
//     let endDay = 1;
//     let endingDate = new Date(2022, 7, endDay );
//
//
//     // for (let i = 0; i < 10; i++ ) {
//     startDay = startDay - 14;
//     let startingDate = new Date(2022, 7, startDay );
//     console.log("check" + startDay);
//
//     let valueDay = startingDate.getDate();
//     let valueMonth = startingDate.getMonth();
//       //console.log(startDay);
//       //console.log(startingDate.getDate())
//       //console.log("the month is " + startingDate.getMonth())
//     // }
//     //   if (test < 500) {
//     //     console.log(myfunction(test++));
//     //   } else {
//     //     console.log("finished, current status:" + test);
//     //   }
//
//     console.log("the value of  the day is " + valueDay);
//     console.log("the value of  the month is " + valueMonth);
//     });
// })

app.listen(3000,function() {
  let test = 1;

  const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const loop = async (position) => {
    for (let i = 0; i < 100; i++ ) {

            let startDay = 11;
            let endDay = 22;

            console.log("this is the test praam" + position);
            // for (let i = 0; i < 10; i++ ) {
            startDay = startDay - 14 * i;
            endDay = endDay - 14 * i;
            let startingDate = new Date(2022, 7, startDay );
            let endingDate = new Date(2022, 7, endDay );

            //console.log("check" + startDay);

            let valueStartingDay = startingDate.getDate();
            let valueStartingMonth = startingDate.getMonth();
            let valueEndDay = endingDate.getDate();
            let valueEndMonth = endingDate.getMonth();
            let currentStartYear = startingDate.getYear() + 1900;
            let currentEndYear = endingDate.getYear() + 1900;
            //console.log("chehchchch" + currentEndYear);
            if (currentEndYear == 2020 && valueEndMonth == 3) {
              break;
            }

            // ######
            console.log(myfunction(position,valueStartingMonth, valueStartingDay, valueEndMonth, valueEndDay,currentStartYear, currentEndYear));
            // #######


              //console.log(startDay);
              //console.log(startingDate.getDate())
              //console.log("the month is " + startingDate.getMonth())
            // }
            //   if (test < 500) {
            //     console.log(myfunction(test++));
            //   } else {
            //     console.log("finished, current status:" + test);
            //   }


            console.log("the current process is: " + i);

      await wait(8000)


    }
    console.log("finished");

  }



      //console.log('Hello World');
      //console.log("check");








  //your code to be executed after 1 second
//loop(1);
  cron.schedule('*/10 * * * *', () =>{
    if (test < symbolList.length) {
      loop(test);
    } else {
      console.log("finished, current status:" + test)
    }
    test = test + 1;
    console.log(test);
  })

})
