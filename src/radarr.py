#!/usr/bin/env python3

import json
import logging

import requests

import commons as commons
import logger
from config import config

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

radarr_config = config["radarr"][0]

addMovieNeededFields = ["tmdbId", "year", "title", "titleSlug", "images"]

def setInstance(label):
    global radarr_config
    radarr_instances = config['radarr']
    commons.setLabel(label)

    for instance in radarr_instances:
        if instance["label"] == label:
            radarr_config = instance
            logger.info(f"Radarr instance set to: {label}")
            return

    logger.error(f"Radarr instance with label '{label}' not found. Default instace will be used.")

def getInstance():
    global radarr_config
    return radarr_config

def search(title):
    parameters = {"term": title}
    url = commons.generateApiQuery("radarr", "movie/lookup", parameters)
    logger.info(url)
    req = requests.get(url)
    parsed_json = json.loads(req.text)

    if req.status_code == 200 and parsed_json:
        return parsed_json
    else:
        return False


def giveTitles(parsed_json):
    data = []
    for movie in parsed_json:
        if all(
            x in movie for x in ["title", "overview", "year", "tmdbId"]
        ):
            data.append(
                {
                    "title": movie["title"],
                    "overview": movie["overview"],
                    "poster": movie.get("remotePoster", None),
                    "year": movie["year"],
                    "id": movie["tmdbId"],
                }
            )
    return data


def inLibrary(tmdbId):
    parameters = {}
    req = requests.get(commons.generateApiQuery("radarr", "movie", parameters))
    parsed_json = json.loads(req.text)
    return next((True for movie in parsed_json if movie["tmdbId"] == tmdbId), False)


def addToLibrary(tmdbId, path, qualityProfileId, tags):
    parameters = {"tmdbId": str(tmdbId)}
    req = requests.get(
        commons.generateApiQuery("radarr", "movie/lookup/tmdb", parameters)
    )
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json, path, qualityProfileId, tags))
    add = requests.post(commons.generateApiQuery("radarr", "movie"), data=data, headers={'Content-Type': 'application/json'})
    if add.status_code == 201:
        return True
    else:
        return False


def removeFromLibrary(tmdbId):
    parameters = { 
        "deleteFiles": str(True)
    }
    dbId = getDbIdFromImdbId(tmdbId)
    delete = requests.delete(commons.generateApiQuery("radarr", f"movie/{dbId}", parameters))
    if delete.status_code == 200:
        return True
    else:
        return False


def buildData(json, path, qualityProfileId, tags):
    built_data = {
        "qualityProfileId": int(qualityProfileId),
        "minimumAvailability": radarr_config["minimumAvailability"],
        "rootFolderPath": path,
        "addOptions": {"searchForMovie": radarr_config["search"]},
        "tags": tags,
    }

    for key in addMovieNeededFields:
        built_data[key] = json[key]
    return built_data


def getRootFolders():
    parameters = {}
    req = requests.get(commons.generateApiQuery("radarr", "Rootfolder", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json


def all_movies():
    parameters = {}
    req = requests.get(commons.generateApiQuery("radarr", "movie", parameters))
    parsed_json = json.loads(req.text)

    if req.status_code == 200:
        data = []
        for movie in parsed_json:
            if all(
                x in movie
                for x in ["title", "year", "monitored", "status"]
            ):
                data.append(
                    {
                        "title": movie["title"],
                        "year": movie["year"],
                        "monitored": movie["monitored"],
                        "status": movie["status"]
                    }
                )
        return data
    else:
        return False


def getQualityProfiles():
    parameters = {}
    req = requests.get(commons.generateApiQuery("radarr", "qualityProfile", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json


def getTags():
    parameters = {}
    req = requests.get(commons.generateApiQuery("radarr", "tag", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json
    
def createTag(tag):
    data_json = {
        "id": int(max([t["id"] for t in getTags()], default=0) + 1),
        "label": str(tag)
    }
    add = requests.post(commons.generateApiQuery("radarr", "tag"), json=data_json, headers={'Content-Type': 'application/json'})
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
    

def getDbIdFromImdbId(tmdbId):
    req = requests.get(commons.generateApiQuery("radarr", "movie", {}))
    parsed_json = json.loads(req.text)
    dbId = [f["id"] for f in parsed_json if f["tmdbId"] == tmdbId]
    return dbId[0]