import fullData from './static/data.js';


// First chart setup
var chartDom1 = document.getElementById('main');
var myChart1 = echarts.init(chartDom1, null, {
  renderer: 'canvas',
  useDirtyRect: false
});

// Second chart setup
var chartDom2 = document.getElementById('main2');
var myChart2 = echarts.init(chartDom2, null, {
  renderer: 'canvas',
  useDirtyRect: false
});

const ubidots = new Ubidots();
const COLUMN_PREFIX = ""; 

ubidots.on("ready", () => {
    render();

    ubidots.on('dashboardRefreshed', function () {
        render();
    });
});

function render() {
    // First Chart (Original Data)
    let series1 = buildEchartsSeries(fullData.series);
    let options1 = setOptionsEcharts(series1, fullData.categories);
    myChart1.setOption(options1);

    // Second Chart (Desired Configuration)
    let series2 = buildEchartsSeriesForSecondChart();
    let options2 = setDesiredChartOptions(series2);
    myChart2.setOption(options2);
}

function buildEchartsSeries(series) {
    series.forEach(element => {
        element["type"] = "bar";
        if (COLUMN_PREFIX !== "") {
            element.stack = '<b>' + formatHours(item.data) + '</b>';
        }
        element["emphasis"] = {
            focus: "self"
        };
        let dataLength = element.data.length;
        let newData = Array(dataLength);
        for (let i = 0; i < dataLength; i++) {
            if (element.data[i] != null) {
                newData[i] = element.data[i];
            }
        }
        element.data = newData;
    });
    return series;
}

function buildEchartsSeriesForSecondChart() {
    const dummyData = generateDummyData();

    return [
        {
            name: "Sample Series",
            type: "line",
            data: dummyData,
            areaStyle: {},
            itemStyle: {
                color: "#5470C6",
                opacity: 0.8,
                borderColor: "#5470C6"
            },
            lineStyle: {
                width: 2
            },
            showSymbol: false,
            symbolSize: 8,
            connectNulls: true
        }
    ];
}

function setOptionsEcharts(series, categories) {
    return {
        tooltip: {
            trigger: 'axis',
            textStyle: {},
            axisPointer: {
                type: 'shadow' // 'shadow' as default; can also be 'line' or 'shadow'
            },
            formatter: function (params) {
                var tooltip = params[0].name + '<br>'; // Category name
                params.forEach(function (item) {
                    if (item.data != null) {
                        tooltip += item.marker + item.seriesName + ':   ' + '<b>' + formatHours(item.data) + '</b>' + '<br>';
                    }
                });
                return tooltip; // Return the customized tooltip content
            }
        },
        legend: {},
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: categories
        },
        yAxis: {
            type: 'value'
        },
        series: series
    };
}

function setDesiredChartOptions(series) {
    return {
        yAxis: [
            {
                type: "value",
                axisLine: {
                    lineStyle: {
                        color: "#5e5e5e40"
                    }
                },
                axisLabel: {
                    color: "#5E5E5E",
                    fontSize: 11,
                    show: false
                },
                splitLine: {
                    lineStyle: {
                        color: ["#5e5e5e"],
                        opacity: 0.1
                    }
                },
                min: "dataMin",
                max: "dataMax",
                name: "",
                nameLocation: "center",
                nameGap: 70,
                nameTextStyle: {
                    color: "#5E5E5E"
                },
                position: "left",
                show: true,
                offset: 0,
                lineStyle: {
                    color: "#5470C6",
                    width: 3
                }
            }
        ],
        xAxis: [
            {
                type: "time",
                axisLine: {
                    lineStyle: {
                        color: "#5e5e5e40"
                    }
                },
                axisLabel: {
                    color: "#5E5E5E",
                    fontSize: 11,
                    show: false
                },
                splitLine: {
                    lineStyle: {
                        color: ["#5e5e5e"],
                        opacity: 0.1
                    }
                }
            }
        ],
        dataZoom: [
            {
                show: true,
                filterMode: "none",
                xAxisIndex: 0,
                realtime: false,
                textStyle: {
                    color: "#5E5E5E",
                    fontSize: 11
                },
                dataBackground: {
                    areaStyle: {
                        color: "#5E5E5E"
                    }
                },
                right: 45,
                left: 45
            }
        ],
        series: series,
        tooltip: {
            confine: true,
            trigger: "axis"
        },
        visualMap: {
            show: false,
            type: "piecewise",
            pieces: [
                { gt: 0, lt: 18, color: "#1e13e8" },
                { gt: 18, lt: 22, color: "#e8dd13" },
                { gt: 22, lt: 26, color: "#e85a13" },
                { gt: 26, lt: 28, color: "#ed2005" },
                { gt: 28, color: "#ed2005" }
            ],
            dimension: 1,
            seriesIndex: 0
        }
    };
}

function generateDummyData() {
    const now = new Date();
    const data = [];
    for (let i = 0; i < 50; i++) {
        const timestamp = new Date(now.getTime() - i * 3600000); // Subtract i hours
        const value = Math.random() * 30; // Random values
        data.push([timestamp, value]); // Push [timestamp, value]
    }
    return data.reverse(); // Ensure chronological order
}

function formatHours(hours) {
    if (hours < 1) {
        return Math.floor(hours * 60) + 'm';
    }
    var duration = moment.duration(hours, 'hours');
    var months = Math.floor(duration.asMonths());
    duration.subtract(months, 'months');
    var days = Math.floor(duration.asDays());
    duration.subtract(days, 'days');
    var remainingHours = Math.floor(duration.asHours());
    duration.subtract(hours, 'hours');
    var minutes = Math.floor(duration.asMinutes());
    var result = '';
    if (months > 0) result += months + 'M ';
    if (days > 0) result += days + 'd ';
    if (remainingHours > 0) result += remainingHours + 'h ';
    if (minutes > 0) result += minutes + 'm';
    return result.trim();
}

window.addEventListener('resize', function () {
    myChart1.resize();
    myChart2.resize();
});