import math

# inputs
radius = 2000.0 # m - the following code is an approximation that stays reasonably accurate for distances < 100km
centerLat = 51.357397146246264 # latitude of circle center, decimal degrees
centerLon = -0.20153965352074504 # Longitude of circle center, decimal degrees

# parameters
N = 10 # number of discrete sample points to be generated along the circle

# generate points
circle_points = []
for k in xrange(N):
    # compute
    angle = math.pi*2*k/N
    dx = radius*math.cos(angle)
    dy = radius*math.sin(angle)
    point = {}
    point['lat']=centerLat + (180/math.pi)*(dy/6378137)
    point['lon']=centerLon + (180/math.pi)*(dx/6378137)/math.cos(centerLat*math.pi/180)
    # add to list
    circle_points.append(point)

for point in circle_points:
    print("{0},{1}".format(point["lat"], point["lon"]))
