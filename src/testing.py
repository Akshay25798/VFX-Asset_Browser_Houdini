#testing json

from itertools import count
import json
import requests
import os

##

workpath = os.path.join(os.path.dirname(__file__))

download_folder = os.path.dirname(workpath) + "\\downloads\\"

json_folder = download_folder + "json\\"
main_api =  "https://api.polyhaven.com/"


def write_json_to_local():
    assets_types = ["hdris", "textures", "models"]
    # thumsnails_file = "https://cdn.polyhaven.com/asset_img/thumbs/"
    # asset_file = "https://api.polyhaven.com/files/"
    # asset_catagories_json = "https://api.polyhaven.com/assets?t=hdris&c=studio"
    for type in assets_types:
        assets_json = main_api + "assets?t=%s" % (type)
        categories_json =  main_api + "categories/%s" %(type)

        assets_json_data = requests.get(assets_json).json()
        categories_json_data = requests.get(categories_json).json()
        local_assets_json_file = json_folder + type + ".json"
        local_categories_json_file = json_folder + type + "_catagories.json"

        with open(local_assets_json_file, 'w', encoding='utf-8') as file: #json for assets full data
            json.dump(assets_json_data, file, ensure_ascii=False, indent=4)

        with open(local_categories_json_file, 'w', encoding='utf-8') as file:#json for catagories only 
            json.dump(categories_json_data, file, ensure_ascii=False, indent=4)

def get_cagagories():
    catagory = "night"
    json_file =  json_folder + "hdris.json"
    print(json_file)
    with open(json_file, "r") as read_content:
        d = json.load(read_content)
        for c in d.keys():
            if catagory in (d[c]["categories"]):
                print(c)




# write_json_to_local()
# get_cagagories()

json_file = json_folder + "hdris_catagories.json"

with open(json_file, "r") as read_content:
    d = json.load(read_content)
    print(len(d.keys()))
