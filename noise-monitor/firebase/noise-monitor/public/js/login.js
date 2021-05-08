//Login Authentication Using Firebase Username/Password

function login(){
    var email = document.getElementById("UNAME").value;
    var password = document.getElementById("PASSWORD").value;

    firebase.auth().signInWithEmailAndPassword(email, password)
    .then((userCredential) => {
      // Signed in
      var user = userCredential.user;
      console.log('signed in');
      
      window.location = "index.html";
      // ...
    })
    .catch((error) => {
      var errorCode = error.code;
      var errorMessage = error.message;
      alert(errorMessage);

    });

}

//Log Off Authentication Using Firebase
function logOff(){
    firebase.auth().signOut().then(() => {
        // Sign-out successful.
        window.location = 'login.html';
        alert('Logged out successfully.');
        
      }).catch((error) => {
        // An error happened.
      });
}

firebase.auth().onAuthStateChanged(firebaseUser => {
    if(firebaseUser && window.location.pathname == '/login.html'){
        window.location = 'index.html';
    }else if(!firebaseUser && window.location.pathname != '/login.html'){
        window.location = 'login.html';
}
});
