import xml.etree.ElementTree as ET
import glob
import csv

from bng_to_latlon import OSGB36toWGS84

ns = {
    'gml': 'http://www.opengis.net/gml/3.2',
    'road': 'http://namespaces.os.uk/Open/Roads/beta2',
    'net': 'urn:x-inspire:specification:gmlas:Network:3.2',
    'tn-ro': 'urn:x-inspire:specification:gmlas:RoadTransportNetwork:3.0'
}

with open("roads.csv", "a") as roads_file:
    writer = csv.writer(roads_file, delimiter = ",")
    writer.writerow(["id", "type", "lat", "lon"])

    # for file in glob.glob("oproad_gml3_gb/data/*.gml"):
    file = "oproad_gml3_gb/data/OSOpenRoads_TQ.gml"
    print(file)

    tree = ET.parse(file)
    root = tree.getroot()

    for member in root.findall("gml:featureMember", ns):
        road_link = member.find("road:RoadLink", ns)
        road_node = member.find("road:RoadNode", ns)
        if road_node is not None:
            pos = road_node.find("net:geometry/gml:Point/gml:pos", ns)
            id = road_node.get("{http://www.opengis.net/gml/3.2}id").replace("id_", "")
            road_type = road_node.find("tn-ro:formOfRoadNode", ns)

            x, y = [int(float(x)) for x in pos.text.split(" ")]
            lat, long = OSGB36toWGS84(x, y)
            # print id, road_type.text, lat, long
            writer.writerow([id, road_type.text, lat, long])
