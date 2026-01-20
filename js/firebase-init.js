// public/js/firebase-init.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";

const firebaseConfig = {

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional

  apiKey: "AIzaSyBokU1u4hJIxZ0Y4U9BxQreI3hnxEJzuwc",
  authDomain: "kid-sequencer.firebaseapp.com",
  projectId: "kid-sequencer",
  storageBucket: "kid-sequencer.firebasestorage.app",
  messagingSenderId: "715996068165",
  appId: "1:715996068165:web:84e127454cb9bb0c35a62c",
  measurementId: "G-3JRQKLK31R"
};


export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
