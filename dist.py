import math
from flask import render_template
import flask

app = flask.Flask('my app')

lat = 51.357397146246264
long = -0.20153965352074504

lat_metres = 2000
long_metres = 100

lat_1 = lat + (lat_metres * 0.0000089)
long_1 = long + (long_metres * 0.0000089 / math.cos(lat * 0.018))

lat_2 = lat_1 + ((lat_metres/3) * 0.0000089)
long_2 = long_1 + (long_metres*3 * 0.0000089 / math.cos(lat_1 * 0.018))


runs = [
    {"latitude": lat, "longitude": long},
    {"latitude": lat_1, "longitude": long_1},
    {"latitude": lat_2, "longitude": long_2},
    {"latitude": lat, "longitude": long}
]

for run in runs:
    print(run)

with app.app_context():
    rendered = render_template('leaflet.html', runs=runs)

    with open("/tmp/map.html", "wb") as file:
        file.write(rendered.encode('utf-8'))
