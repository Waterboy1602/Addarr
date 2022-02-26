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

config = config["sonarr"]

addSerieNeededFields = ["tvdbId", "tvRageId", "title", "titleSlug", "images", "seasons"]


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
            for x in ["title", "statistics", "remotePoster", "year", "tvdbId"]
        ):
            data.append(
                {
                    "title": show["title"],
                    "seasonCount": show["statistics"]["seasonCount"],
                    "poster": show["remotePoster"],
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
        "languageProfileId": getLanguageProfileId(config["languageProfile"]),
        "addOptions": {
            "ignoreEpisodesWithFiles": "true",
            "ignoreEpisodesWithoutFiles": "false",
            "searchForMissingEpisodes": config["search"],
        },
        "rootFolderPath": path,
        "seasonFolder": config["seasonFolder"],
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
        "id": max([t["id"] for t in getTags()])+1,
        "label": str(tag)
    }
    add = requests.post(commons.generateApiQuery("sonarr", "tag"), json=data_json, headers={'Content-Type': 'application/json'})
    if add.status_code == 200:
        return True
    else:
        return False

def getLanguageProfileId(language):
    parameters = {}
    req = requests.get(commons.generateApiQuery("sonarr", "languageProfile", parameters))
    parsed_json = json.loads(req.text)
    languageId = [l["id"] for l in parsed_json if l["name"] == language]
    return languageId[0]
    
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