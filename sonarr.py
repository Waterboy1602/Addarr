#!/usr/bin/env python3

import commons as commons
import json
import logging
import requests
import yaml

from definitions import CONFIG_PATH, LOG_PATH

log = logging
log.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=LOG_PATH,
    filemode="a",
    level=logging.INFO,
)

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))
config = config["sonarr"]

addSerieNeededFields = ["tvdbId", "tvRageId", "title", "titleSlug", "images", "seasons"]


def search(title):
    parameters = {"term": title}
    req = requests.get(commons.generateApiQuery("sonarr", "series/lookup", parameters))
    parsed_json = json.loads(req.text)

    if req.status_code == 200:
        return parsed_json
    else:
        return False


def giveTitles(parsed_json):
    data = []
    for show in parsed_json:
        if all(
            x in show
            for x in ["title", "seasonCount", "remotePoster", "year", "tvdbId"]
        ):
            data.append(
                {
                    "title": show["title"],
                    "seasonCount": show["seasonCount"],
                    "poster": show["remotePoster"],
                    "year": show["year"],
                    "id": show["tvdbId"],
                }
            )
    return data


def returnVal(rawjson):
    totalData = []
    seriesList = rawjson
    for show in seriesList:
        specShow = seriesList[show]
        totalData.append(
            specShow["title"],
            specShow["itvDb"],
            specShow["remotePoster"],
            specShow["seasonCount"],
            specShow["year"],
        )
    return totalData


def inLibrary(tvdbId):
    parameters = {}
    req = requests.get(commons.generateApiQuery("sonarr", "series", parameters))
    parsed_json = json.loads(req.text)
    return next((True for show in parsed_json if show["tvdbId"] == tvdbId), False)


def addToLibrary(tvdbId):
    parameters = {"term": "tvdb:" + str(tvdbId)}
    req = requests.get(commons.generateApiQuery("sonarr", "series/lookup", parameters))
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json))
    add = requests.post(commons.generateApiQuery("sonarr", "series"), data=data)
    if add.status_code == 201:
        return True
    else:
        return False


def buildData(json):
    built_data = {
        "qualityProfileId": config["qualityProfileId"],
        "addOptions": {
            "ignoreEpisodesWithFiles": "true",
            "ignoreEpisodesWithoutFiles": "false",
            "searchForMissingEpisodes": config["search"],
        },
        "rootFolderPath": config["rootFolder"],
        "seasonFolder": config["seasonFolder"],
    }

    for show in json:
        for key, value in show.items():
            if key in addSerieNeededFields:
                built_data[key] = value
    return built_data
