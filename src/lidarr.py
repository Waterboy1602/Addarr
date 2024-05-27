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

addMusicNeededFields = ["id", "term"]

def search(artistName):
    logger.debug("Searching for artist: " + artistName)
    parameters = {"term": artistName}
    url = commons.generateApiQuery("lidarr", "artist/lookup", parameters, 1)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)

    if req.status_code == 200 and parsed_json:
        return parsed_json
    else:
        return False


def giveResults(parsed_json):
    logger.debug("Found the following artists:")
    data = []
    for artist in parsed_json:
        if all(
            x in artist
            for x in ["artistName", "statistics", "foreignArtistId", "artistType"]
        ):
            poster = next((image['remoteUrl'] for image in artist['images'] if image['coverType'] in ['poster', 'fanart']), None)
            if(poster == None and len(artist["images"]) > 0):
                poster = artist["images"][0]['remoteUrl'] # If no poster or fanart found, take the first image if there is one

            data.append(
                {
                    "artistName": artist["artistName"],
                    "albumCount": artist["statistics"]["albumCount"],
                    "poster": poster,
                    "id": artist["foreignArtistId"],
                    "monitored": artist["monitored"],
                    "status": artist["status"],
                    "type": artist["artistType"],
                }
            )
            logger.debug(artist["artistName"])
    return data


def inLibrary(id):
    logger.debug("Checking if artist is in library")
    parameters = {}
    url = commons.generateApiQuery("lidarr", "artist", parameters, 1)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)
    return next((True for artist in parsed_json if artist["foreignArtistId"] == id), False)


def addToLibrary(id, path, qualityProfileId, tags):
    logger.debug("Adding artist to library")
    parameters = {"term": "lidarr:" + str(id)}
    url = commons.generateApiQuery("lidarr", "artist/lookup", parameters, 1)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json, path, qualityProfileId, tags))
    url2 = commons.generateApiQuery("lidarr", "artist", 1)
    logger.info(url2)
    add = requests.post(url2, data=data, headers={'Content-Type': 'application/json'})
    if add.status_code == 201:
        return True
    else:
        return False


def removeFromLibrary(dbId):
    logger.debug("Removing artist from library")
    parameters = {
        "deleteFiles": str(True)
    }
    delete = requests.delete(commons.generateApiQuery("lidarr", f"artist/{dbId}", parameters, 1))
    if delete.status_code == 200:
        return True
    else:
        return False


def buildData(json, path, qualityProfileId, tags): # debug here!!!!!!!!!
    logger.debug("Building data")

    built_data = {
        "qualityProfileId": qualityProfileId,
        "addOptions": {
            "addType": "automatic",
            "searchForNewAlbum": True

        },
        "rootFolderPath": path,
        "monitored": True,
        "tags": tags,
    }

    for artist in json:
        for key, value in artist.items():
            if key in addMusicNeededFields:
                built_data[key] = value

    logger.debug(f"Query endpoint is: {commons.generateApiQuery('lidarr', 'artist', 1)}")
    return built_data

def getRootFolders():
    logger.debug("Getting root folders")
    parameters = {}
    url = commons.generateApiQuery("lidarr", "Rootfolder", parameters, 1)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)
    # Remove unmappedFolders from rootFolder data--we don't need that
    for item in [
        item for item in parsed_json if item.get("unmappedFolders") is not None
    ]:
        item.pop("unmappedFolders")
    return parsed_json


def allArtists():
    logger.debug("Getting all artists")
    parameters = {}
    url = commons.generateApiQuery("lidarr", "artist", parameters, 1)
    logger.info(url)
    req = requests.get(url)
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
    url = commons.generateApiQuery("lidarr", "qualityProfile", parameters, 1)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)
    return parsed_json


def getTags():
    logger.debug("Getting tags")
    parameters = {}
    url = commons.generateApiQuery("lidarr", "tag", parameters, 1)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)
    return parsed_json


def createTag(tag):
    # logger.debug("Creating tag")
    # data_json = {
    #     "id": int(max([t["id"] for t in getTags()], default=0)+1),
    #     "label": str(tag)
    # }
    # url = commons.generateApiQuery("lidarr", "tag", 1)
    # logger.info(url)
    # add = requests.post(url, json=data_json, headers={'Content-Type': 'application/json'})
    # if add.status_code == 200:
    #     return True
    # else:
    #     return False
    return False # Not implemented yet