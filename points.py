from haversine import haversine
import random
import math

def generate_points(centerLat, centerLon, radius, N=10):
    circle_points = []
    for k in xrange(N):
        angle = math.pi * 2 * k / N
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        point = {}
        point['lat'] = centerLat + (180 / math.pi) * (dy / 6378137)
        point['lon'] = centerLon + (180 / math.pi) * (dx / 6378137) / math.cos(centerLat * math.pi / 180)
        circle_points.append(point)
    return circle_points

estimated_distance = 10000
points_to_generate = 200
lat = 51.357397146246264
lon = -0.20153965352074504

low_index = random.randint(0, points_to_generate)-1

points = generate_points(lat, lon, estimated_distance / 4, points_to_generate)
low = points[low_index]

for point in points:
    point["distanceFromLowIndex"] = haversine((point["lat"], point["lon"]), (low["lat"], low["lon"])) * 1000

for point in sorted(points, key=lambda point: point["distanceFromLowIndex"]):
    print(point)