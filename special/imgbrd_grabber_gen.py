
import argparse
import json
import os
import sys

from special.ConfigArgParser import ConfigParser

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--sort', action="store_true",
                    help="Sorts the list of entries.")
parser.add_argument('--batch_path', default="~/Batches/",
                    help="input for the folder name. will use settings.txt if not omitted.")
parser.add_argument('-w', '--web', default="e621.net",
                    help="input the website. will use settings.txt if not omitted.")
parser.add_argument('--max', type=int, default=1000,
                    help="max images to give per item. will use settings.txt if not omitted.")
cparser = ConfigParser(parser, "config.json", autofill=True)
args = cparser.parse_args()

if not os.path.exists("prefixes.txt"):
    raise FileNotFoundError(
        "You don't have a prefixes.txt file! (a prompt per line)")
with open("prefixes.txt", "r") as prfile:
    prefixes = prfile.readlines()
    prfile.close()

prefixes = [i.strip().split(" ") for i in prefixes]

assert len(prefixes) > 0, "Your prefixes.txt is empty. Fill it up with prompts"

outputJson = {
    "batchs": [],
    "uniques": [],
    "version": 3
}

for prompt in prefixes:
    tmpdict = {
        'filename': "%search%/%date:format=yyyy-MM-dd-hh-mm-ss%_%md5%_%rating%.%ext%",
        'galleriesCountAsOne': True, 'getBlacklisted': False,
        'page': 1, 'perpage': 60,
        'path': args.batch_path,
        'postFiltering': [
            "-piss"
        ],
        'query': {
            'tags': prompt
        },
        'site': args.web,
        "total": args.max}
    outputJson['batchs'].append(tmpdict)


with open("imgbrd_grabbergen.igl", "w") as outfile:
    outfile.write(json.dumps(outputJson, indent=4))
    outfile.close()
