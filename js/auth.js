// public/js/auth.js
import { auth } from "./firebase-init.js";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";

function $(id) { return document.getElementById(id); }

const els = {
  email: $("email"),
  password: $("password"),
  msg: $("authMsg"),
  signupBtn: $("signupBtn"),
  loginBtn: $("loginBtn"),
  logoutBtn: $("logoutBtn"),
  goBtn: $("goToAppBtn"),
};

function setMsg(text) {
  if (!els.msg) return;
  els.msg.textContent = text || "";
}

function setAuthedUI(user) {
  const isAuthed = !!user;

  if (els.logoutBtn) els.logoutBtn.style.display = isAuthed ? "inline-block" : "none";
  if (els.goBtn) els.goBtn.style.display = isAuthed ? "inline-block" : "none";
}

async function handleSignup() {
  const email = els.email?.value?.trim();
  const password = els.password?.value;

  if (!email || !password) return setMsg("Enter email and password.");
  setMsg("Creating account...");

  try {
    await createUserWithEmailAndPassword(auth, email, password);
    setMsg("Account created. Redirecting...");
    window.location.href = "./index.html";
  } catch (e) {
    setMsg(e?.message || "Sign up failed.");
  }
}

async function handleLogin() {
  const email = els.email?.value?.trim();
  const password = els.password?.value;

  if (!email || !password) return setMsg("Enter email and password.");
  setMsg("Signing in...");

  try {
    await signInWithEmailAndPassword(auth, email, password);
    setMsg("Signed in. Redirecting...");
    window.location.href = "./index.html";
  } catch (e) {
    setMsg(e?.message || "Login failed.");
  }
}

async function handleLogout() {
  try {
    await signOut(auth);
    setMsg("Signed out.");
  } catch (e) {
    setMsg(e?.message || "Logout failed.");
  }
}

// Wire buttons
els.signupBtn?.addEventListener("click", (e) => { e.preventDefault(); handleSignup(); });
els.loginBtn?.addEventListener("click", (e) => { e.preventDefault(); handleLogin(); });
els.logoutBtn?.addEventListener("click", (e) => { e.preventDefault(); handleLogout(); });
els.goBtn?.addEventListener("click", (e) => { e.preventDefault(); window.location.href = "./index.html"; });

// Keep UI in sync
onAuthStateChanged(auth, (user) => {
  setAuthedUI(user);
  if (user) setMsg(`Signed in as ${user.email}`);
});
