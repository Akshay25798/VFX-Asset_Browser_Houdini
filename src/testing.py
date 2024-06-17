#testing json

import json
import os

json_file = r"D:\PYTHON\TEST\clock.json"

with open(json_file, "r") as read_content:
    j = json.load(read_content)
    for i in j.keys():
        print(i)
    for i in j['usd']:
        print(i)
    for i in j['usd']['2k']['usd']['include']:
        print(i)
        for k in j['usd']['2k']['usd']['include'][i]:
            print(j['usd']['2k']['usd']['include'][i]['url'])

    # print(j['usd']['2k']['usd']['url'])

