<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Login</title>
  <style>
    body{
      font-family: "Trebuchet MS", Arial, sans-serif;
      background: #f6fbff;
      margin: 0;
      min-height: 100vh;
      display:flex;
      align-items:center;
      justify-content:center;
      padding: 18px;
      box-sizing:border-box;
    }
    .card{
      background:#ffffff;
      border: 4px solid #1d1d1d;
      border-radius: 18px;
      box-shadow: 0 16px 0 rgba(0,0,0,0.10);
      padding: 22px 24px;
      width: min(520px, 92vw);
      text-align:center;
    }
    h1{
      margin: 0 0 10px 0;
      font-size: 20px;
      font-weight: 900;
    }
    p{
      margin: 0 0 16px 0;
      font-weight: 800;
      opacity: 0.75;
      font-size: 13px;
    }
    button{
      width: 180px;
      height: 56px;
      border-radius: 16px;
      border: 4px solid #1d1d1d;
      background:#ffffff;
      box-shadow: 0 10px 0 rgba(0,0,0,0.07);
      font-weight: 900;
      font-size: 18px;
      cursor:pointer;
      color:#18b118;
      transition: transform 120ms ease;
    }
    button:hover{ transform: translateY(-1px); }
    .smallLink{
      display:inline-block;
      margin-top: 12px;
      font-weight: 900;
      color:#1f2a44;
      text-decoration:none;
      opacity:0.85;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Login</h1>
    <p>Press continue to unlock the greyed-out features.</p>
    <button id="continueBtn" type="button">Continue</button>
    <a class="smallLink" href="javascript:history.back()">Back</a>
  </div>

  <script>
    const params = new URLSearchParams(location.search);
    const returnTo = params.get("return") || "index.html";

    document.getElementById("continueBtn").addEventListener("click", () => {
      try{ localStorage.setItem("kidseq_logged_in","1"); }catch(e){}
      location.href = returnTo;
    });
  </script>
</body>
</html>
