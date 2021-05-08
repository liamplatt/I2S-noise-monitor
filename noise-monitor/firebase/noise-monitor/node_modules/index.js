const functions = require("firebase-functions");

// The Firebase Admin SDK to access Firestore.
const admin = require('firebase-admin');
admin.initializeApp();

// REST API (GET)- noiseLevel
// Description: Receives room data and stores in database
// Inputs: room, noise_level, status
// Output: Firestore created alert ID
 exports.noiseLevel = functions.https.onRequest(async(request, response) => {

  // Get inputs
  const room = request.query.room;
  const noise_level = request.query.noise;
  const status = request.query.status;

  // Save inputs in firestore
  const writeResult = await admin.firestore().collection('alerts').add({
    'noise_level':noise_level,
    'status':status,
    'room':room,
    'type': 'noise',
    'time_stamp':admin.firestore.FieldValue.serverTimestamp()

  });

  // Respond with alert/record id
  response.send('Alert created with ID: '+ writeResult.id);

 });


 // Trigger Function updateRoomStatus
 // Trigger: Document created into alerts collection
 // Description: Updates the room data (status, updated, last_db_recorded) with the last alert information
 exports.updateRoomStatus = functions.firestore.document('/alerts/{documentId}')
    .onCreate((snap, context) => {
      // Grab the current value of what was written to Firestore.
      const room = snap.data().room; 
      const status = snap.data().status;
      const time = snap.data().time_stamp;
      const last_db_recorded = snap.data().noise_level;
      
      // Create data that will be updated
      const data = {
        status:status,
        updated: time,
        last_db_recorded:last_db_recorded
      };
      
      // Update room record
      return admin.firestore().collection('rooms').doc(room).update(data);
    });

 