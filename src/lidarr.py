#!/usr/bin/env python3

import json
import logging

import requests

import commons as commons
import logger
from config import config

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.lidarr", logLevel, config.get("logToConsole", False))

config = config["lidarr"]

addMusicNeededFields = ["id", "tvRageId", "term", "termSlug", "images", "seasons"]

def search(artistName):
    logger.debug("Searching for artist: " + artistName)
    parameters = {"term": artistName}
    url = commons.generateApiQuery("lidarr", "artist/lookup", parameters)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)

    if req.status_code == 200 and parsed_json:
        return parsed_json
    else:
        return False


def giveTitles(parsed_json):
    logger.debug("Found the following artists:")
    data = []
    for artist in parsed_json:
        if all(
            x in artist
            for x in ["term", "statistics", "year", "tvdbId"]
        ):
            data.append(
                {
                    "term": artist["term"],
                    "seasonCount": artist["statistics"]["seasonCount"],
                    "poster": artist.get("remotePoster", None),
                    "year": artist["year"],
                    "id": artist["tvdbId"],
                    "monitored": artist["monitored"],
                    "status": artist["status"],
                }
            )
    return data


def inLibrary(id):
    logger.debug("Checking if artist is in library")
    parameters = {}
    req = requests.get(commons.generateApiQuery("lidarr", "series", parameters))
    parsed_json = json.loads(req.text)
    return next((True for artist in parsed_json if artist["id"] == id), False)


def addToLibrary(id, path, qualityProfileId, tags, seasonsSelected):
    parameters = {"term": "id:" + str(id)}
    req = requests.get(commons.generateApiQuery("lidarr", "artist/lookup", parameters))
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json, path, qualityProfileId, tags, seasonsSelected))
    add = requests.post(commons.generateApiQuery("lidarr", "artist"), data=data, headers={'Content-Type': 'application/json'})
    if add.status_code == 201:
        return True
    else:
        return False


def removeFromLibrary(dbId):
    logger.debug("Removing artist from library")
    parameters = {
        "deleteFiles": str(True)
    }
    delete = requests.delete(commons.generateApiQuery("lidarr", f"artist/{dbId}", parameters))
    if delete.status_code == 200:
        return True
    else:
        return False


def buildData(json, path, qualityProfileId, tags, seasonsSelected):
    logger.debug("Building data")
#    "languageProfileId": getLanguageProfileId(config["languageProfile"]),
    built_data = {
        "qualityProfileId": qualityProfileId,
        "addOptions": {
            "ignoreEpisodesWithFiles": True,
            "ignoreEpisodesWithoutFiles": False,
            "searchForMissingEpisodes": config["search"],
        },
        "rootFolderPath": path,
        "seasonFolder": config["seasonFolder"],
        "monitored": True,
        "tags": tags,
        "seasons": seasonsSelected,
    }
    for artist in json:
        for key, value in artist.items():
            if key in addMusicNeededFields:
                built_data[key] = value
            if key == "seasons": built_data["seasons"] = seasonsSelected
    logger.debug(f"Query endpoint is: {commons.generateApiQuery('lidarr', 'artist')}")
    return built_data


def getRootFolders():
    logger.debug("Getting root folders")
    parameters = {}
    req = requests.get(commons.generateApiQuery("lidarr", "Rootfolder", parameters))
    parsed_json = json.loads(req.text)
    # Remove unmappedFolders from rootFolder data--we don't need that
    for item in [
        item for item in parsed_json if item.get("unmappedFolders") is not None
    ]:
        item.pop("unmappedFolders")
    return parsed_json


def allMusic():
    logger.debug("Getting all artists")
    parameters = {}
    req = requests.get(commons.generateApiQuery("lidarr", "artist", parameters))
    parsed_json = json.loads(req.text)

    if req.status_code == 200:
        data = []
        for artist in parsed_json:
            if all(
                x in artist
                for x in ["term", "year", "monitored", "status"]
            ):
                data.append(
                    {
                        "term": artist["term"],
                        "year": artist["year"],
                        "monitored": artist["monitored"],
                        "status": artist["status"],
                    }
                )
        return data
    else:
        return False


def getQualityProfiles():
    logger.debug("Getting quality profiles")
    parameters = {}
    req = requests.get(commons.generateApiQuery("lidarr", "qualityProfile", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json


def getTags():
    logger.debug("Getting tags")
    parameters = {}
    req = requests.get(commons.generateApiQuery("lidarr", "tag", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json


def createTag(tag):
    logger.debug("Creating tag")
    data_json = {
        "id": int(max([t["id"] for t in getTags()], default=0)+1),
        "label": str(tag)
    }
    add = requests.post(commons.generateApiQuery("lidarr", "tag"), json=data_json, headers={'Content-Type': 'application/json'})
    if add.status_code == 200:
        return True
    else:
        return False


def getLanguageProfileId(language):
    logger.debug("Getting language profile id")
    parameters = {}
    req = requests.get(commons.generateApiQuery("lidarr", "languageProfile", parameters))
    parsed_json = json.loads(req.text)
    languageId = [l["id"] for l in parsed_json if l["name"] == language]
    if len(languageId) == 0:
        languageId = [l["id"] for l in parsed_json]
        logger.debug("Didn't find a match with languageProfile from the config file. Took instead the first languageId from languageProfile-API response")
    return languageId[0]