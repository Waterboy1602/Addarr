#!/usr/bin/env python3

import json
import logging

import requests

import commons as commons
import logger
from config import config

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.sonarr", logLevel, config.get("logToConsole", False))

sonarr_config = config["sonarr"][0]

addSerieNeededFields = ["tvdbId", "tvRageId", "title", "titleSlug", "images", "seasons"]

def setInstance(label):
    global sonarr_config
    sonarr_instances = config['sonarr']
    commons.setLabel(label)

    for instance in sonarr_instances:
        if instance["label"] == label:
            sonarr_config = instance
            logger.info(f"Sonarr instance set to: {label}")
            return

    logger.error(f"Sonarr instance with label '{label}' not found. Default instace will be used.")

def getInstance():
    global sonarr_config
    return sonarr_config

def search(title):
    parameters = {"term": title}
    req = requests.get(commons.generateApiQuery("sonarr", "series/lookup", parameters))
    parsed_json = json.loads(req.text)

    if req.status_code == 200 and parsed_json:
        return parsed_json
    else:
        return False


def giveTitles(parsed_json):
    data = []
    for show in parsed_json:
        if all(
            x in show
            for x in ["title", "statistics", "year", "tvdbId"]
        ):
            data.append(
                {
                    "title": show["title"],
                    "seasonCount": show["statistics"]["seasonCount"],
                    "poster": show.get("remotePoster", None),
                    "year": show["year"],
                    "id": show["tvdbId"],
                    "monitored": show["monitored"],
                    "status": show["status"],
                }
            )
    return data


def inLibrary(tvdbId):
    parameters = {}
    req = requests.get(commons.generateApiQuery("sonarr", "series", parameters))
    parsed_json = json.loads(req.text)
    return next((True for show in parsed_json if show["tvdbId"] == tvdbId), False)


def addToLibrary(tvdbId, path, qualityProfileId, tags, seasonsSelected):
    parameters = {"term": "tvdb:" + str(tvdbId)}
    req = requests.get(commons.generateApiQuery("sonarr", "series/lookup", parameters))
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json, path, qualityProfileId, tags, seasonsSelected))
    add = requests.post(commons.generateApiQuery("sonarr", "series"), data=data, headers={'Content-Type': 'application/json'})
    if add.status_code == 201:
        return True
    else:
        return False


def removeFromLibrary(tvdbId):
    parameters = { 
        "deleteFiles": str(True)
    }
    dbId = getDbIdFromImdbId(tvdbId)
    delete = requests.delete(commons.generateApiQuery("sonarr", f"series/{dbId}", parameters))
    if delete.status_code == 200:
        return True
    else:
        return False


def buildData(json, path, qualityProfileId, tags, seasonsSelected):
    built_data = {
        "qualityProfileId": qualityProfileId,
        "addOptions": {
            "ignoreEpisodesWithFiles": True,
            "ignoreEpisodesWithoutFiles": False,
            "searchForMissingEpisodes": sonarr_config["search"],
        },
        "rootFolderPath": path,
        "seasonFolder": sonarr_config["seasonFolder"],
        "monitored": True,
        "tags": tags,
        "seasons": seasonsSelected,
    }
    for show in json:
        for key, value in show.items():
            if key in addSerieNeededFields:
                built_data[key] = value
            if key == "seasons": built_data["seasons"] = seasonsSelected
    logger.debug(f"Query endpoint is: {commons.generateApiQuery('sonarr', 'series')}")
    return built_data


def getRootFolders():
    parameters = {}
    req = requests.get(commons.generateApiQuery("sonarr", "Rootfolder", parameters))
    parsed_json = json.loads(req.text)
    # Remove unmappedFolders from rootFolder data--we don't need that
    for item in [
        item for item in parsed_json if item.get("unmappedFolders") is not None
    ]:
        item.pop("unmappedFolders")
    return parsed_json


def allSeries():
    parameters = {}
    req = requests.get(commons.generateApiQuery("sonarr", "series", parameters))
    parsed_json = json.loads(req.text)

    if req.status_code == 200:
        data = []
        for show in parsed_json:
            if all(
                x in show
                for x in ["title", "year", "monitored", "status"]
            ):
                data.append(
                    {
                        "title": show["title"],
                        "year": show["year"],
                        "monitored": show["monitored"],
                        "status": show["status"],
                    }
                )
        return data
    else:
        return False


def getQualityProfiles():
    parameters = {}
    req = requests.get(commons.generateApiQuery("sonarr", "qualityProfile", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json


def getTags():
    parameters = {}
    req = requests.get(commons.generateApiQuery("sonarr", "tag", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json

def createTag(tag):
    data_json = {
        "id": int(max([t["id"] for t in getTags()], default=0) + 1),
        "label": str(tag)
    }
    add = requests.post(commons.generateApiQuery("sonarr", "tag"), json=data_json, headers={'Content-Type': 'application/json'})
    response_content = json.loads(add.content.decode('utf-8'))
    if add.status_code == 200:
        return response_content["id"]
    else:
        return -1
    
def tagExists(tag):
    tags = getTags()
    for item in tags:
        if item['label'] == str(tag).lower():
            return item['id']
    return -1

def getSeasons(tvdbId):
    parameters = {"term": "tvdb:" + str(tvdbId)}
    req = requests.get(commons.generateApiQuery("sonarr", "series/lookup", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json[0]["seasons"]


def getDbIdFromImdbId(tvdbId):
    req = requests.get(commons.generateApiQuery("sonarr", "series", {}))
    parsed_json = json.loads(req.text)
    dbId = [f["id"] for f in parsed_json if f["tvdbId"] == tvdbId]
    return dbId[0]
