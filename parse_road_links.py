import xml.etree.ElementTree as ET
import glob
import csv

from bng_to_latlon import OSGB36toWGS84

ns = {
    'gml': 'http://www.opengis.net/gml/3.2',
    'road': 'http://namespaces.os.uk/Open/Roads/beta2',
    'net': 'urn:x-inspire:specification:gmlas:Network:3.2',
    'tn-ro': 'urn:x-inspire:specification:gmlas:RoadTransportNetwork:3.0',
    'xlink': 'http://www.w3.org/1999/xlink'
}

with open("oproad_gml3_gb/data/OSOpenRoads_TQ.gml", "r") as roads_file:
    tree = ET.parse(roads_file)
    root = tree.getroot()

with open("road_links.csv", "a") as road_links_file:
    writer = csv.writer(road_links_file, delimiter = ",")
    writer.writerow(["start_id", "end_id", "length", "name", "classification", "classification_number"])
    for member in root.findall("gml:featureMember", ns):
        road_link = member.find("road:RoadLink", ns)
        if road_link is not None:
            start_node = road_link.find("net:startNode", ns)
            end_node = road_link.find("net:endNode", ns)
            start_id = start_node.get("{http://www.w3.org/1999/xlink}href").replace("#", "")
            end_id = end_node.get("{http://www.w3.org/1999/xlink}href").replace("#", "")
            road_length_element = road_link.find("road:length", ns)
            road_length = road_length_element.text if road_length_element is not None else ""
            road_name_element = road_link.find("road:name1", ns)
            road_name = road_name_element.text if road_name_element is not None else ""
            road_classification_element = road_link.find("road:roadClassification", ns)
            road_classification = road_classification_element.text if road_classification_element is not None else ""
            road_classification_number_element = road_link.find("road:roadClassificationNumber", ns)
            road_classification_number = road_classification_number_element.text if road_classification_number_element is not None else ""
            print(start_id, end_id)
            writer.writerow([start_id, end_id, road_length, road_name, road_classification, road_classification_number])
