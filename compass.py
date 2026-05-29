# V4.1

#################################################################
##########################CONFIGURATION##########################

SCAN_DISTANCE = None                          # Meters or None
SCAN_ENTRIES = 3                              # Number

#################################################################
#################################################################

import re, pyperclip, time, os, json, requests, math, ntplib, csv
from typing import Dict, Any, List, Iterable
from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass
class AtlasEntry:
    System: str
    ObjectContainer: str
    Type: str
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
PLANETARY_TYPES = {"Planet", "Moon"}
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

def nearest_entry(atlas: Iterable, x: float, y: float, z: float, allowed_types=None):
    if allowed_types is not None:
        filtered = [e for e in atlas if getattr(e, "Type", None) in allowed_types]
        if filtered:
            atlas = filtered
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

def ensure_waypoint_template(source_file="waypoints.csv", template_file="waypoint.csv"):
    if os.path.exists(source_file) or os.path.exists(template_file):
        return
    with open(template_file, "w", encoding="utf-8", newline="") as f:
        f.write("showlocation,nearest,system,name\n")

def append_waypoint(entry: Dict[str, str], file_path="waypoints.csv"):
    file_exists = os.path.exists(file_path)
    with open(file_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["showlocation", "nearest", "system", "name"])
        writer.writerow([
            entry["showlocation"],
            entry["nearest"],
            entry["system"],
            entry.get("name", ""),
        ])

def matching_waypoints(nearest: str, system: str, file_path="waypoints.csv"):
    if not os.path.exists(file_path):
        return []
    results = []
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_nearest = (row.get("nearest") or "").strip().casefold()
            row_system = (row.get("system") or "").strip().casefold()
            if row_nearest == nearest.strip().casefold() and row_system == system.strip().casefold():
                results.append(row)
    return results

def parse_latlon(showlocation: str):
    parts = [p.strip() for p in showlocation.split(",")]
    if len(parts) != 2:
        return None
    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        return None

def waypoint_name(row: Dict[str, str]):
    return (
        (row.get("name") or row.get("waypoint") or row.get("label") or "").strip()
        or "(unnamed)"
    )

atlas = [
    AtlasEntry(
        System=entry["System"],
        ObjectContainer=entry["ObjectContainer"],
        Type=entry["Type"],
        XCoord=entry["XCoord"],
        YCoord=entry["YCoord"],
        ZCoord=entry["ZCoord"],
        BodyRadius=entry["BodyRadius"],
        RotationSpeedX=entry["RotationSpeedX"],
        RotationAdjustmentX=entry["RotationAdjustmentX"]
    )
    for entry in open_book("atlas.json", "https://starmap.space/api/v4/oc")
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
ensure_waypoint_template()
os.system("title Skylarker Compass")
os.system('cls')
print("\nRun /showlocation while on a planetary or moon surface and cut '/save' text to save that location;\nI'm watching your clipboard… (Ctrl+C to quit)\n")
last_snapshot = None
try:
    while True:
        text = pyperclip.paste().strip()
        if text.lower() == "/save" and text != last_text:
            last_text = text
            os.system('cls')
            if last_snapshot is None:
                print("No planetary /showlocation data yet. Copy a planetary or moon surface /showlocation result first.")
            else:
                append_waypoint(last_snapshot)
                print("Saved waypoint to waypoints.csv:")
                print(f"  showlocation : {last_snapshot['showlocation']}")
                print(f"  nearest      : {last_snapshot['nearest']}")
                print(f"  system       : {last_snapshot['system']}")
            time.sleep(0.25)
            continue
        match = pattern.search(text)
        if match and text != last_text:
            last_text = text
            x, y, z = match.groups()
            x, y, z = float(x), float(y), float(z)
            surface_bodies = [
                e for e in atlas
                if e.Type in PLANETARY_TYPES
            ]
            if surface_bodies:
                Planet = nearest_entry(surface_bodies, x, y, z)
            else:
                Planet = nearest_entry(atlas, x, y, z, allowed_types=PLANETARY_TYPES)
            PlanetName = Planet.ObjectContainer
            PlanetX = Planet.XCoord
            PlanetY = Planet.YCoord
            PlanetZ = Planet.ZCoord
            PlanetR = Planet.BodyRadius
            PlanetS = Planet.RotationSpeedX
            PlanetA = Planet.RotationAdjustmentX
            ox, oy, oz = x - PlanetX, y - PlanetY, z - PlanetZ
            r = math.sqrt(ox*ox + oy*oy + oz*oz)
            on_surface = PlanetS and PlanetR > 0 and r <= (PlanetR * 1.20)
            if on_surface:
                scale = PlanetR / r
                sx, sy, sz = ox * scale, oy * scale, oz * scale
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
                last_snapshot = {
                    "showlocation": f"{lat_display:+.6f},{lon180:+.6f}",
                    "nearest": PlanetName,
                    "system": Planet.System,
                }
                print(f"    Nearby signatures...")
                printed_any = False
                for entry, dist in pings:
                    printed_any = True
                    print(f"      {entry.PoiName:<50} is {dist:>8,.0f}m away @{bearing(lat,lon360,entry.Latitude,entry.Longitude360):.0f}°")
                matches = matching_waypoints(PlanetName, Planet.System)
                print("    Matching waypoints...")
                if matches:
                    for row in matches:
                        waypoint_latlon = parse_latlon((row.get("showlocation") or "").strip())
                        if waypoint_latlon is None:
                            continue
                        waypoint_lat_display, waypoint_lon180 = waypoint_latlon
                        waypoint_lat = -waypoint_lat_display
                        waypoint_lon360 = (waypoint_lon180 + 360.0) % 360.0
                        waypoint_dist = haversine(lat, lon360, waypoint_lat, waypoint_lon360, PlanetR)
                        waypoint_bearing = bearing(lat, lon360, waypoint_lat, waypoint_lon360)
                        printed_any = True
                        print(
                            f"      {waypoint_name(row):<50} is {waypoint_dist:>8,.0f}m away @{waypoint_bearing:.0f}°"
                        )
                else:
                    print("      ...none")
                if not printed_any:
                    print(f"      ...nothing here")
            else:
                last_snapshot = None
                os.system('cls')
                print("||| Nothing here... |||")
        time.sleep(0.25)
except KeyboardInterrupt:
    print("\nBye!")
