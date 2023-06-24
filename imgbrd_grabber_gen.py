import json
from pathlib import Path
import typer
from cfg_param_wrapper import wrap_config, CfgDict
from copy import deepcopy

cfg_dct = {  # this does not automatically generate for some reason
    "batchs_template": {
        "filename": "%search_1%/%date:format=yyyy-MM-dd-hh-mm-ss%_%md5%_%rating%.%ext%",
        "galleriesCountAsOne": True,
        "getBlacklisted": False,
        "page": 1,
        "perpage": 60,
        "path": "Batches",
        "site": "e621.net",
        "total": 1000,
        "query": {
            "tags": ["-watersports", "-urine", "-gore", "-vore", "-loli"],
        },
        "postFiltering": [],
    }
}
cfg_path = Path("imgbrd_grabber.json")
if not cfg_path.exists():
    with cfg_path.open("w") as f:
        json.dump(cfg_dct, f, indent=4)

cfg = CfgDict(
    "imgbrd_grabber.json",
    cfg_dct,
)


@wrap_config(cfg)
def create_imgbrd_lst(
    prefixes_path: Path = Path("prefixes.txt"),
):
    prefixes = Path(prefixes_path).read_text().splitlines()
    assert prefixes, "Your prefixes.txt is empty. Fill it up with prompts"

    outputJson = {"batchs": [], "uniques": [], "version": 3}
    for prompt in prefixes:
        print(prompt)

        dct = deepcopy(cfg["batchs_template"])
        if "tags" not in dct.get("query", []):
            dct["query"] = {"tags": [prompt]}
        else:
            dct["query"]["tags"] = [*prompt.split(" "), *dct["query"]["tags"]]
        outputJson["batchs"].append(dct)

    with open("imgbrd_grabbergen.igl", "w", encoding="utf-8") as outfile:
        outfile.write(json.dumps(outputJson, indent=4))


if __name__ == "__main__":
    typer.run(create_imgbrd_lst)
