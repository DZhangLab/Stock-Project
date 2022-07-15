$(document).ready(function() {


//var calendarpicker = Metro.getPlugin(element, 'calendarpicker');
//
//console.log(calendarpicker.getSelected());
//console.log("test");
var transaction_x = apple.map(x => x["timePoint"]);
var transaction_y = apple.map(x => x["minuteOpen"]);
console.log(apple[1]);
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
console.log("testststststts");

const labels = transaction_x;
  const data = {
    labels: labels,
    datasets: [{
      label: 'my first dataset',
      backgroundColor: 'rgb(255, 99, 132)',
      borderColor: 'rgb(265,99, 132)',
      data: transaction_y,
      fill: false
    }]
  };

  const config = {
    type: 'line',
    data: data,
    options: {}
  };
const myChart = new Chart(
      document.getElementById('myChart'),
      config
    );




var dataPoints = [];
var chart = new CanvasJS.Chart("chartContainer", {
	theme: "light2", // "light1", "dark1", "dark2"
	animationEnabled: true,
	exportEnabled: true,
	zoomEnabled: true,
	title: {
		text: "Starbucks Corporation Stock Price"
	},
	subtitles: [{
		text: "2012 - 2017"
	}],
	axisX: {
		valueFormatString: "YYYY"
	},
	axisY: {
		title: "Price (in USD)",
		prefix: "$"
	},
	data: [{
		type: "candlestick",
		xValueType: "dateTime",
		xValueFormatString: "mm-HH-DD-MMM-YYYY",
		yValueFormatString: "$#,##0.00",
		dataPoints: dataPoints
	}]
});
for (var i = 0; i < timepoint.length; i++) {
		dataPoints.push({
			x: timepoint[i],
			y: apple[i]
		});
	}

chart.render();

//function parseData(result) {
//	for (var i = 0; i < result.length; i++) {
//		dataPoints.push({
//			x: result[i].x,
//			y: result[i].y
//		});
//	}
//	chart.render();
//}




})