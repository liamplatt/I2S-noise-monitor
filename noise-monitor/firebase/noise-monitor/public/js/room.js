const urlParams = new URLSearchParams(window.location.search);
const room = urlParams.get('room')
var roomData;

const TIME_WINDOW = 2*60*1000; //2 minutes in milli


// Dorm Rooms data for front end
var app = new Vue({
    el: '#room',
    data: {
      room: {}
    },
    mounted(){
        //room details
        const ref = firebase.firestore().collection('rooms').doc(room);
        ref.onSnapshot(snapshot => {
            var updated_date = snapshot.data().updated.toDate();
            var is_connected = ((new Date) - updated_date) < TIME_WINDOW;

           let data = snapshot.data();
            data.id = room;
            data.connected = is_connected;
            this.room = data;
            roomData = data;
            //console.log(this.room);
            });
    }
  });
  //Query Data From Firebase to Chart
  //get alerts
  //var compareDate; //24 hours before now
  var yesterday = new Date(new Date().getTime() - (24 * 60 * 60 * 1000));
  var room_alerts =[];
  firebase.firestore().collection("alerts").where("room", "==", room).where("time_stamp", ">", yesterday)
  .get()
  .then((querySnapshot) => {
      querySnapshot.forEach((doc) => {
          // doc.data() is never undefined for query doc snapshots
          var data = {
              x:doc.data().time_stamp.toDate(),
              y:parseFloat(doc.data().noise_level)
          };

          //console.log(doc.id, " => ", doc.data());
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


  //Executing Notification Button
   function sendNotifications(){

    let residentIDs = roomData.residents;

    for (i = 0; i < residentIDs.length; i++) {

        var docRef = firebase.firestore().collection("users").doc(residentIDs[i]);
         docRef.get().then((doc) => {
            if (doc.exists) {
                
                sendEmail(doc.data());

            } else {
                // doc.data() will be undefined in this case
                console.log("No such document!");
            }
        }).catch((error) => {
            console.log("Error getting document:", error);
        });

      }

      alert("mail sent successfully"); 

  }

  function generateEmails(data){
    let domains = ["@txt.att.net","@tmomail.net","@messaging.sprintpcs.com","@vtext.com","@vmobl.com"];
    let emails = [];

    for(i =0; i < domains.length;i++){
        emails.push(data.phone_number+domains[i]);
    }

    return emails;
    
  }


  //send email
   function sendEmail(data){ 

        //get recipients
        let phone_emails = generateEmails(data);

        //get status
        let noise_status = roomData.status;
        let connected = roomData.connected; 
        let updated = roomData.updated;

        //get decibels
        let db = Math.round(roomData.last_db_recorded);

        //Body
        var body;
        if(connected){
            //noise alert
            body = "ALERT! Room "+room+".\n Status: "+noise_status+".\n Last Decibel reading: "+db+".\n Last Updated: "+updated.toDate().toString();
        }else{
            //connection alert
            body = "ALERT! Room "+room+" is not properly connected. Please check connection.\n Last Status: "+noise_status+".\n Last Decibel reading: "+db+".\n Last Updated: "+updated.toDate(); 
        }

		Email.send
			({ 
	    		Host: "smtp.gmail.com", 
				Username: "uhartreslife1@gmail.com", 
				Password: "ynnfujqccvcjfyyc", 
				To: data.email, 
                Bcc: phone_emails,
				From: "uhartreslife1@gmail.com", 
				Subject: "University of Hartford Residential Life", 
				Body: body ,			
			}) 
			.then(function (message) { 
			    
			}); 


	} 
  