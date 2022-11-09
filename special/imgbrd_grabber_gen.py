
import argparse
import json
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--sort', action="store_true",
                    help="Sorts the list of entries.")
parser.add_argument(
    '-i', '--input', help="input for the folder name. will use settings.txt if not omitted.")
parser.add_argument(
    '-w', '--web', help="input the website. will use settings.txt if not omitted.")
parser.add_argument(
    '--max', help="max images to give per item. will use settings.txt if not omitted.")
args = parser.parse_args()

defaultPaths = ["e621.net",
                os.path.dirname(os.path.realpath(__file__)), "1000"]
defaultPaths = "\n".join(defaultPaths)
if not (args.input or args.web or args.max):
    if not os.path.exists("settings.txt"):
        print("settings not detected, touching with filler settings...")
        with open("settings.txt", "w") as settings:
            settings.write(defaultPaths)
            settings.close()
        sys.exit(1)
    else:
        with open("settings.txt", "r") as settings:
            settings_files = [i.strip() for i in settings.readlines()]
            args.web = settings_files[0]
            args.input = settings_files[1]
            args.max = int(settings_files[2])
            settings.close()

assert os.path.exists(
    "prefixes.txt"), "You don't have a prefixes.txt file! (a prompt per line)"
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
        'path': args.input,
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
