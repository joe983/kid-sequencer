// Firebase init (v10 modular CDN)
// 1) Paste your Firebase web config values below (from Firebase Console -> Project settings -> Your apps -> Web app).
// 2) Make sure Authentication is enabled (Email/Password at minimum).
// 3) If you want user data stored, enable Firestore Database as well.

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import { getAuth, setPersistence, browserLocalPersistence } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBokU1u4hJIxZ0Y4U9BxQreI3hnxEJzuwc",
  authDomain: "kid-sequencer.firebaseapp.com",
  projectId: "kid-sequencer",
  storageBucket: "kid-sequencer.firebasestorage.app",
  messagingSenderId: "715996068165",
  appId: "1:715996068165:web:84e127454cb9bb0c35a62c",
  measurementId: "G-3JRQKLK31R"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// Keep users signed in across refreshes (and across tabs)
setPersistence(auth, browserLocalPersistence).catch(() => {
  // ignore (e.g., private browsing / blocked storage)
});

export { app, auth, db };
