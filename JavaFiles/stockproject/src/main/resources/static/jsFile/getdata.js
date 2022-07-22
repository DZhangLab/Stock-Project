$(document).ready(function() {


//var calendarpicker = Metro.getPlugin(element, 'calendarpicker');
//
//console.log(calendarpicker.getSelected());
//console.log("test");
var transaction_x = apple.map(x => x["timePoint"]);
var transaction_y = apple.map(x => x["minuteOpen"]);
// console.log(apple[1]);
//console.log(timepoint);
//console.log(apple[1]["minuteOpen"]);



// create the object to passinto chart js package.








function myFunction(sel, day, el){
        console.log(sel)
                console.log("test")

        console.log(day)
        console.log("test")
        console.log(el)
    }
function showAlert() {
    alert("The button was clicked!");
}
//console.log("testststststts");
//
//const labels = transaction_x;
//  const data = {
//    labels: labels,
//    datasets: [{
//      label: 'my first dataset',
//      backgroundColor: 'rgb(255, 99, 132)',
//      borderColor: 'rgb(265,99, 132)',
//      data: transaction_y,
//      fill: false
//    }]
//  };
//
//  const config = {
//    type: 'line',
//    data: data,
//    options: {}
//  };
//const myChart = new Chart(
//      document.getElementById('myChart'),
//      config
//    );




var dataPoints = [];
var dataPoints2 = [];
for (var i = 0; i < timepoint.length; i++) {
        //console.log(i);
        ///console.log(apple[i][1]);
		dataPoints.push({
			x: new Date(timepoint[i]),
			y: [Number(apple[i][0]), Number(apple[i][1]), Number(apple[i][2]), Number(apple[i][3])]

		});
		dataPoints2.push({x: new Date(timepoint[i]), y: Number(apple[i][3])});
	}

  console.log(dataPoints);

//function parseData(result) {
//	for (var i = 0; i < result.length; i++) {
//		dataPoints.push({
//			x: result[i].x,
//			y: result[i].y
//		});
//	}
//	chart.render();
//}

//console.log(dataPoints);

  var dps1 = [], dps2= [];
  var stockChart = new CanvasJS.StockChart("chartContainer",{
    title:{
      text:"Stock chart for apple"
    },
    subtitles: [{
      text:"Simple Moving Average"
    }],
    charts: [{
      axisY: {
        prefix: "$"
      },
      legend: {
        verticalAlign: "top",
        cursor: "pointer",
        itemclick: function (e) {
          if (typeof (e.dataSeries.visible) === "undefined" || e.dataSeries.visible) {
            e.dataSeries.visible = false;
          } else {
            e.dataSeries.visible = true;
          }
          e.chart.render();
        }
      },
      toolTip: {
        shared: true
      },
      data: [{
        type: "candlestick",
        showInLegend: true,
        name: "Stock Price",
        yValueFormatString: "$#,###.00",
        xValueType: "dateTime",
        xValueFormatString: "YYYY-MMM-DD HH:mm ",
        dataPoints : dataPoints
      }],
    }]
  });

//  $.getJSON("https://canvasjs.com/data/docs/ethusd2018.json", function(data) {
//    for(var i = 0; i < data.length; i++){
//      dps1.push({x: new Date(data[i].date), y: [Number(data[i].open), Number(data[i].high), Number(data[i].low), Number(data[i].close)]});
//      dps2.push({x: new Date(data[i].date), y: Number(data[i].close)});
//    }
//
  stockChart.render();

var sma = calculateSMA(dataPoints, 7);
stockChart.charts[0].addTo("data", { type: "line", dataPoints: sma, showInLegend: true, yValueFormatString: "$#,###.00", name: "Simple Moving Average"})
//  });
  function calculateSMA(dps, count){
    var avg = function(dps){
      var sum = 0, count = 0, val;
      for (var i = 0; i < dps.length; i++) {
        val = dps[i].y[3]; sum += val; count++;
      }
      return sum / count;
    };
    var result = [], val;
    count = count || 5;
    for (var i=0; i < count; i++)
      result.push({ x: dps[i].x , y: null});
    for (var i=count - 1, len=dps.length; i < len; i++){
      val = avg(dps.slice(i - count + 1, i));
      if (isNaN(val))
        result.push({ x: dps[i].x, y: null});
      else
        result.push({ x: dps[i].x, y: val});
    }
    return result;
  }
  console.log(dps1);
setTimeout(function() {
  //your code to be executed after 1 second
}, 100000);


})