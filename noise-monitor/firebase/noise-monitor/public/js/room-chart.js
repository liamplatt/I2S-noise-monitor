
var myChart;


//Calendar Function
  function updateDate(){
    room_alerts =[];

    var currentDate = $( "#datepicker" ).datepicker( "getDate" );
    var endDay = new Date(currentDate.getTime() + (24 * 60 * 60 * 1000));

    var docRef = firebase.firestore().collection("alerts")
    .where("room", "==", room)
    .where("time_stamp", ">", currentDate)
    .where("time_stamp", "<", endDay)
      .get()
      .then((querySnapshot) => {
          querySnapshot.forEach((doc) => {
              // doc.data() is never undefined for query doc snapshots
              var data = {
                x:doc.data().time_stamp.toDate(),
                y:parseFloat(doc.data().noise_level)
            };

            room_alerts.push(data);
          });

          if(myChart){
            myChart.destroy();
        }
  
        createChart(room_alerts);
      })
      .catch((error) => {
          console.log("Error getting documents: ", error);
      });
  }


  //Chart JS
  function createChart(data){
    var ctx = document.getElementById('myChart').getContext('2d');
    myChart = new Chart(ctx, {
      type: 'line',
      data: {
         // labels: [new Date('2019-01-01'), new Date('2019-01-02'),new Date('2019-02-05')],
        datasets: [{
          label: 'My Line',
          data: data,
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor:'rgb(75, 192, 192,0.5)',
          lineTension: 1
        }]
      },
      options: {
                  responsive: true,
                  title:{
                      display:false,
                      text:"Noise over time"
                  },
                  legend:{
                    display:false
                  },
                  elements: {
                    point:{
                        radius: 0
                    }
                },

                annotation: {
                  annotations: [{
                  type: 'line',
                  mode: 'horizontal',
                  scaleID: 'Y',
                  value: 90,
                  borderColor: '#E53030',
                  borderWidth: 2,
                  label: {
                    enabled: true,
                    content: 'Loud'
                  }
                },
                {
                  type: 'line',
                  mode: 'horizontal',
                  scaleID: 'Y',
                  value: 70,
                  borderColor: '#FFC107',
                  borderWidth: 2,
                  label: {
                    enabled: true,
                    content: 'Warning'
                  }
                }
              ]
              },

        scales: {
                      xAxes: [{
                          type: 'time',
                          display: true,
                          ticks: {
                              source:'auto',
                              maxTicksLimit: 24,
                              fontColor:'white'
                           },
                          scaleLabel: {
                              display: false,
                              labelString: 'Date'
                          },
                          gridLines: {
                            display: false ,
                            color: 'white'
                          },
                      }],
                      yAxes: [{
                          display: true,
                          id:'Y',
                          ticks:{
                            fontColor: "white",
                            suggestedMax: 95,
                          },
                          scaleLabel: {
                              display: true,
                              labelString: 'Decibels',
                              fontColor:'white'
                          },
                          gridLines: {
                            display: false ,
                            color: 'white'
                          },
                      }]
                  }
      }
    });
  }