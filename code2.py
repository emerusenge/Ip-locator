from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests, threading, smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from time import sleep
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)
app.secret_key = 'secret123'

SENDER_EMAIL = "emerusengechanelle664@gmail.com"
APP_PASSWORD = "mtgo qhqp rnnw tfsb"
BUJUMBURA = {'lat': -3.3822, 'lon': 29.3644}

countries_progress = []
seen_countries = set()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return round(2 * asin(sqrt(a)) * R, 2)

def get_ip_geolocation(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,city,lat,lon", timeout=5)
        data = res.json()
        if data.get("status") == "success":
            return {
                "country_name": data["country"],
                "city": data["city"],
                "latitude": data["lat"],
                "longitude": data["lon"]
            }
    except:
        pass

    try:
        res = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        data = res.json()
        if 'latitude' in data and 'longitude' in data:
            return {
                "country_name": data.get("country_name"),
                "city": data.get("city"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude")
            }
    except:
        pass

    return None

def get_altitude(lat, lon):
    try:
        r = requests.get(f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}", timeout=5)
        if r.ok:
            return r.json()["results"][0]["elevation"]
    except:
        pass
    return None

def reverse_country(lat, lon):
    try:
        r = requests.get(f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=fr", timeout=5)
        if r.ok:
            return r.json().get("countryName")
    except:
        pass
    return None

def get_province(lat, lon):
    try:
        r = requests.get(
            f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1",
            headers={'User-Agent': 'GeoApp'}, timeout=5
        )
        if r.ok:
            data = r.json()
            return data.get('address', {}).get('state')
    except:
        pass
    return None

def send_email(subject, body, user_email=None, html=False):
    try:
        recipients = [SENDER_EMAIL]
        if user_email:
            recipients.append(user_email)

        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        if html:
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
    except Exception as e:
        print(f"Erreur envoi email : {e}")

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "1234":
            session["user"] = "admin"
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Identifiants incorrects.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/localisation")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", year=datetime.now().year)

@app.route("/start_path", methods=["POST"])
def start_path():
    if "user" not in session:
        return jsonify({"error": "Non autorisé"}), 403

    ip = request.form.get("ip")
    user_email = request.form.get("email")
    geo = get_ip_geolocation(ip)

    if not geo:
        return jsonify({"error": "Impossible de localiser l'IP"}), 400

    lat, lon = geo["latitude"], geo["longitude"]
    altitude = get_altitude(lat, lon)
    distance = haversine(BUJUMBURA['lat'], BUJUMBURA['lon'], lat, lon)
    flight_time = round(distance / 900, 2)

    global countries_progress, seen_countries
    countries_progress = []
    seen_countries = set()

    destination_country = geo["country_name"]
    destination_city = geo["city"]
    provinces_traversees = []

    # Déterminer la source et la destination selon la logique demandée
    if destination_country.lower() == "burundi":
        source = "Bujumbura Mairie"
        destination = destination_city or "Ville inconnue"
    else:
        source = "Burundi"
        destination = destination_country

    def detect_path(user_email):
        global countries_progress, seen_countries
        steps = 30
        seen_provinces = set()

        for i in range(steps + 1):
            frac = i / steps
            cur_lat = BUJUMBURA['lat'] + frac * (lat - BUJUMBURA['lat'])
            cur_lon = BUJUMBURA['lon'] + frac * (lon - BUJUMBURA['lon'])

            country = reverse_country(cur_lat, cur_lon)
            if country and country not in seen_countries:
                countries_progress.append({"name": country, "lat": cur_lat, "lon": cur_lon})
                seen_countries.add(country)

            if destination_country.lower() == "burundi":
                province = get_province(cur_lat, cur_lon)
                if province and province not in seen_provinces:
                    provinces_traversees.append(province)
                    seen_provinces.add(province)

            if country == destination_country:
                break

            sleep(0.1)

        countries_list = [c['name'] for c in countries_progress]

        html_body = f"""
        <html>
        <head><style>
          body {{ font-family: Arial, sans-serif; background-color: #f9f9f9; color: #333; padding: 20px; }}
          h2 {{ color: #2c3e50; }}
          ul {{ background-color: #ecf0f1; border-radius: 8px; padding: 15px; list-style-type: none; }}
          li {{ padding: 8px 0; border-bottom: 1px solid #bdc3c7; }}
          li:last-child {{ border-bottom: none; }}
        </style></head>
        <body>
          <h2>Résultat du trajet</h2>
          <p><strong>Source :</strong> {source}</p>
          <p><strong>Destination :</strong> {destination}</p>
          <p><strong>Pays traversés :</strong></p>
          <ul>{''.join(f'<li>{country}</li>' for country in countries_list)}</ul>
        """

        if provinces_traversees:
            html_body += f"""
              <p><strong>Provinces traversées  :</strong></p>
              <ul>{''.join(f'<li>{prov}</li>' for prov in provinces_traversees)}</ul>
            """

        html_body += "</body></html>"

        send_email("Résultat du trajet", html_body, user_email, html=True)

    threading.Thread(target=detect_path, args=(user_email,)).start()

    return jsonify({
        "ip": ip,
        "city": destination_city,
        "country_name": destination_country,
        "latitude": lat,
        "longitude": lon,
        "altitude": altitude,
        "distance_km": distance,
        "flight_time": flight_time,
        "source": source,
        "destination": destination,
        "path": [{"lat": BUJUMBURA['lat'], "lon": BUJUMBURA['lon']}, {"lat": lat, "lon": lon}],
        "provinces": provinces_traversees if destination_country.lower() == "burundi" else []
    })

@app.route("/progress")
def progress():
    if "user" not in session:
        return jsonify({"error": "Non autorisé"}), 403
    return jsonify(countries_progress)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
