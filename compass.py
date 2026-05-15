# V3.0

#################################################################
##########################CONFIGURATION##########################

SCAN_DISTANCE = None                          # Meters or None
SCAN_ENTRIES = 3                              # Number

#################################################################
#################################################################

import re, pyperclip, time, os, json, requests, math, ntplib
from typing import Dict, Any, List, Iterable
from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass
class AtlasEntry:
    ObjectContainer: str
    XCoord: float
    YCoord: float
    ZCoord: float
    BodyRadius: float
    RotationSpeedX: float
    RotationAdjustmentX: float
    
@dataclass
class PoiEntry:
    Planet: str
    PoiName: str
    Latitude: float
    Longitude360: float
    Introduced: float

def haversine(lat1, lon1, lat2, lon2, R):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

old = ["Alpha 3.4.0"]
pattern = re.compile(r"""
    x\s*:\s*(?P<x>[-+]?\d+(?:\.\d+)?)\s*
    y\s*:\s*(?P<y>[-+]?\d+(?:\.\d+)?)\s*
    z\s*:\s*(?P<z>[-+]?\d+(?:\.\d+)?)
""", re.IGNORECASE | re.VERBOSE)
last_text = None
client = ntplib.NTPClient()
response = client.request("pool.ntp.org", version=3)
epoch = datetime.strptime("01.01.2020 00:00.00", "%d.%m.%Y %H:%M.%S").replace(tzinfo=timezone.utc)
utc = datetime.fromtimestamp(response.tx_time, tz=timezone.utc)
system_utc = datetime.now(timezone.utc)
offset = utc - system_utc

def now():
    return datetime.now(timezone.utc) + offset

def bearing(lat1, lon1, lat2, lon2):
    # Convert to radians
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δλ = math.radians(lon2 - lon1)

    x = math.sin(Δλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - (math.sin(φ1) * math.cos(φ2) * math.cos(Δλ))

    θ = math.atan2(x, y)
    bearing = (math.degrees(θ) + 360) % 360
    return bearing

def nearest_entry(atlas: Iterable, x: float, y: float, z: float):
    nearest = min(
        atlas,
        key=lambda e: (e.XCoord - x)**2 + (e.YCoord - y)**2 + (e.ZCoord - z)**2
    )
    return nearest

def nearest_pois(database, lat, lon, r, planet, n=SCAN_ENTRIES, max_d=SCAN_DISTANCE):
    filtered = [
        (e, haversine(lat, lon, e.Latitude, e.Longitude360, r))
        for e in database
        if getattr(e, "Planet", None) == planet
        and getattr(e, "Introduced", None) not in old
    ]
    if max_d is not None:
        filtered = [(e, d) for e, d in filtered if d <= max_d]
    sorted_entries = sorted(filtered, key=lambda x: x[1])
    return sorted_entries[:n]


def open_book(book, location) -> List[Dict[str, Any]]:
    if os.path.exists(book):
        with open(book, "r", encoding="utf-8") as f:
            return json.load(f)
    resp = requests.get(location, headers={"Accept": "application/json"}, timeout=20)
    resp.raise_for_status()
    data_json = resp.json()
    if isinstance(data_json, dict) and "results" in data_json:
        data_json = data_json["results"]
    elif isinstance(data_json, dict):
        data_json = list(data_json.values())
    with open(book, "w", encoding="utf-8") as f:
        json.dump(data_json, f, ensure_ascii=False, separators=(",", ":"))
    return data_json

atlas = [
    AtlasEntry(
        ObjectContainer=entry["ObjectContainer"],
        XCoord=entry["XCoord"],
        YCoord=entry["YCoord"],
        ZCoord=entry["ZCoord"],
        BodyRadius=entry["BodyRadius"],
        RotationSpeedX=entry["RotationSpeedX"],
        RotationAdjustmentX=entry["RotationAdjustmentX"]
    )
    for entry in open_book("atlas.json", "https://starmap.space/api/v3/oc")
]
pois = [
    PoiEntry(
        Planet=entry["Planet"],
        PoiName=entry["PoiName"],
        Latitude=entry["Latitude"],
        Longitude360=entry["Longitude360"],
        Introduced=entry["Introduced"]
    )
    for entry in open_book("pois.json", "https://starmap.space/api/v4/pois/")
]
os.system("title Skylarker Compass")
os.system('cls')
print("\nRun /showlocation while on a celestial surface to begin scanning the area around you;\nI'm watching your clipboard… (Ctrl+C to quit)\n")
try:
    while True:
        text = pyperclip.paste()
        match = pattern.search(text)
        if match and text != last_text:
            last_text = text
            x, y, z = match.groups()
            x, y, z = float(x), float(y), float(z)
            Planet = nearest_entry(atlas, x, y, z)
            PlanetName = Planet.ObjectContainer
            PlanetX = Planet.XCoord
            PlanetY = Planet.YCoord
            PlanetZ = Planet.ZCoord
            PlanetR = Planet.BodyRadius
            PlanetS = Planet.RotationSpeedX
            PlanetA = Planet.RotationAdjustmentX
            if PlanetS:
                ox, oy, oz = x - PlanetX, y - PlanetY, z - PlanetZ
                r = math.sqrt(ox*ox + oy*oy + oz*oz)
                scale = PlanetR / r
                sx, sy, sz = ox * scale, oy * scale, oz * scale
                surface_x = PlanetX + sx
                surface_y = PlanetY + sy
                surface_z = PlanetZ + sz
                lat = math.degrees(math.atan2(sz, math.sqrt(sx*sx + sy*sy)))
                lat_display = -lat
                lon360 = (math.degrees(math.atan2(sy, sx)) + 360.0) % 360.0
                frame = ((now()-epoch).total_seconds()/3600)
                rotation_rate = 360 / PlanetS
                rotation = frame * rotation_rate
                rotation_mod = (rotation % 360) + PlanetA
                lon360 = (lon360 - rotation_mod) % 360
                lon180 = ((lon360 + 180.0) % 360.0) - 180.0
                pings = nearest_pois(pois, lat, lon360, PlanetR, PlanetName)
                os.system('cls')
                print(f"||| Scanning {PlanetName}... |||")
                print(f"    Your position is:")
                print(f"      Latitude  : {lat_display:+.2f}")
                print(f"      Longitude : {lon180:+.2f}")
                print(f"    Nearby signatures...")
                for entry, dist in pings:
                    print(f"      {entry.PoiName:<50} is {dist:>8,.0f}m away @{bearing(lat,lon360,entry.Latitude,entry.Longitude360):.0f}°")
                if not pings:
                    print(f"      ...nothing here")
            else:
                os.system('cls')
                print(f"      ...nothing here")
        time.sleep(0.25)
except KeyboardInterrupt:
    print("\nBye!")
