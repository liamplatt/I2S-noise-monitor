
const TIME_WINDOW = 2*60*1000; //2 minutes in milli

var app = new Vue({
    el: '#app',
    data: {
      rooms: []
    },
    mounted(){
        const ref = firebase.firestore().collection('rooms');
        ref.onSnapshot(snapshot => {
            let rooms = [];
              snapshot.forEach(doc => {
                var updated_date = doc.data().updated.toDate();
                var is_connected = ((new Date) - updated_date) < TIME_WINDOW;

                rooms.push(
                    {...doc.data(), 
                        id:doc.id,
                        status:doc.data().status,
                        connected:is_connected
                    
                    });
              });
            this.rooms = rooms;
            });
    }
  })


    
