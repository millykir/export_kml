import requests
import math
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, send_file
import io
import os

app = Flask(__name__, template_folder="templates")
CIRCLE_SEGMENTS = 64   # число вершин для аппроксимации круга

def kml_color_from_hex(hex_color: str, alpha: str = "ff") -> str:
    """
    Преобразует "#RRGGBB" в "aabbggrr" для KML.
    """
    hex_color = hex_color.lstrip('#')
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return (alpha + b + g + r).lower()

def create_placemark(doc: ET.Element, zone: dict):
    name       = zone.get("name", "")
    color      = zone.get("color", "#ffffff")
    labelColor = zone.get("labelColor", "#000000")
    points     = zone.get("points", [])
    radius     = zone.get("r")  # может быть None
    z_type     = zone.get("type")

    pm = ET.SubElement(doc, "Placemark")
    ET.SubElement(pm, "name").text = name
    ET.SubElement(pm, "styleUrl").text = f"#style_{name}"

    desc_lines = [f"Name: {name}", f"Type: {z_type}"]
    if radius is not None:
        desc_lines.append(f"Radius: {radius} m")
    ET.SubElement(pm, "description").text = "\n".join(desc_lines)

    style = ET.SubElement(pm, "Style", id=f"style_{name}")
    ls = ET.SubElement(style, "LineStyle")
    ET.SubElement(ls, "color").text = kml_color_from_hex(color)
    ET.SubElement(ls, "width").text = "2"
    ps = ET.SubElement(style, "PolyStyle")
    ET.SubElement(ps, "color").text = kml_color_from_hex(color, alpha="7f")
    ET.SubElement(ps, "fill").text = "1"
    ET.SubElement(ps, "outline").text = "1"
    lbl = ET.SubElement(style, "LabelStyle")
    ET.SubElement(lbl, "color").text = kml_color_from_hex(labelColor)

    if z_type == 2 and radius is not None and points:
        center = points[0]
        lat0, lon0 = center["lt"], center["ln"]
        coords = []
        for i in range(CIRCLE_SEGMENTS + 1):
            angle = 2 * math.pi * i / CIRCLE_SEGMENTS
            lat = lat0 + (radius / 111320) * math.cos(angle)
            lon = lon0 + (radius / (111320 * math.cos(math.radians(lat0)))) * math.sin(angle)
            coords.append(f"{lon},{lat},0")
        poly = ET.SubElement(pm, "Polygon")
        ET.SubElement(poly, "tessellate").text = "1"
        outer = ET.SubElement(poly, "outerBoundaryIs")
        lin = ET.SubElement(outer, "LinearRing")
        ET.SubElement(lin, "coordinates").text = " ".join(coords)
    else:
        coord_list = [f"{pt['ln']},{pt['lt']},0" for pt in points]
        poly = ET.SubElement(pm, "Polygon")
        ET.SubElement(poly, "tessellate").text = "1"
        outer = ET.SubElement(poly, "outerBoundaryIs")
        lin = ET.SubElement(outer, "LinearRing")
        ET.SubElement(lin, "coordinates").text = " ".join(coord_list)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    api_base = request.form["api_base"].rstrip("/")
    username = request.form["username"]
    password = request.form["password"]
    filename = request.form.get("filename", "geozones.kml")

    auth_url = f"{api_base}/auth/login"
    r = requests.post(auth_url,
                      json={"username": username, "password": password},
                      headers={"Content-Type": "application/json"})
    r.raise_for_status()
    token = r.json().get("data")
    if not token:
        return "Не удалось получить токен", 500

    geo_url = f"{api_base}/geozones/map"
    geo_r = requests.get(geo_url,
                         headers={"Authorization": f"Bearer {token}"})
    geo_r.raise_for_status()
    zones = geo_r.json().get("data", [])

    kml = ET.Element("kml")
    doc = ET.SubElement(kml, "Document")
    ET.SubElement(doc, "name").text = "Geofences"
    for zone in zones:
        create_placemark(doc, zone)
    tree = ET.ElementTree(kml)
    buf = io.BytesIO()
    tree.write(buf, xml_declaration=True, encoding="utf-8", method="xml")
    buf.seek(0)

    return send_file(buf,
                     as_attachment=True,
                     download_name=filename,
                     mimetype="application/vnd.google-earth.kml+xml")

if __name__ == "__main__":
    # В продакшене запускать через gunicorn или waitress
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
