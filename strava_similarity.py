import os
import polyline
import requests
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

token = os.environ["TOKEN"]
headers = {'Authorization': "Bearer {0}".format(token)}


def find_points(activity_id):
    r = requests.get("https://www.strava.com/api/v3/activities/{0}".format(activity_id), headers=headers)
    response = r.json()
    line = response["map"]["polyline"]
    return polyline.decode(line)


activity1_id = 1355676694
activity2_id = 1246017379

distance, path = fastdtw(find_points(activity1_id), find_points(activity2_id), dist=euclidean)
print(distance)
