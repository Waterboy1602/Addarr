#!/usr/bin/env python3

import json
import logging

import requests
from requests.auth import HTTPBasicAuth

import commons as commons
import logger
from config import config

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

config = config["radarr"]

addMovieNeededFields = ["tmdbId", "year", "title", "titleSlug", "images"]


def search(title):
    parameters = {"term": title}
    url = commons.generateApiQuery("radarr", "movie/lookup", parameters)
    logger.info(url)
    
    req = get_req(url)
    parsed_json = json.loads(req.text)

    if req.status_code == 200 and parsed_json:
        return parsed_json
    else:
        return False


def giveTitles(parsed_json):
    data = []
    for movie in parsed_json:
        if all(
            x in movie for x in ["title", "overview", "remotePoster", "year", "tmdbId"]
        ):
            data.append(
                {
                    "title": movie["title"],
                    "overview": movie["overview"],
                    "poster": movie["remotePoster"],
                    "year": movie["year"],
                    "id": movie["tmdbId"],
                }
            )
    return data


def inLibrary(tmdbId):
    parameters = {}
    url = commons.generateApiQuery("radarr", "movie", parameters)

    req = get_req(url)
    parsed_json = json.loads(req.text)
    return next((True for movie in parsed_json if movie["tmdbId"] == tmdbId), False)


def addToLibrary(tmdbId, path, qualityProfileId, tags):
    parameters = {"tmdbId": str(tmdbId)}
    url = commons.generateApiQuery("radarr", "movie/lookup/tmdb", parameters)

    req = get_req(url)
    
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json, path, qualityProfileId, tags))
    url = commons.generateApiQuery("radarr", "movie")
    logger.debug(url)
    logger.debug(data)
    add = post_req(url, data=data, headers={'Content-Type': 'application/json'})
    if add.status_code == 201:
        return True
    else:
        return False


def removeFromLibrary(tmdbId):
    parameters = { 
        "deleteFiles": str(True)
    }
    dbId = getDbIdFromImdbId(tmdbId)
    url = commons.generateApiQuery("radarr", f"movie/{dbId}", parameters)
  
    req = delete_req(url)

    
    if req.status_code == 200:
        return True
    else:
        return False


def buildData(json, path, qualityProfileId, tags):
    built_data = {
        "qualityProfileId": int(qualityProfileId),
        "minimumAvailability": config["minimumAvailability"],
        "rootFolderPath": path,
        "addOptions": {"searchForMovie": config["search"]},
        "tags": tags,
    }

    for key in addMovieNeededFields:
        built_data[key] = json[key]
    return built_data


def getRootFolders():
    parameters = {}
    url = commons.generateApiQuery("radarr", "Rootfolder", parameters)

    req = get_req(url)

    parsed_json = json.loads(req.text)
    return parsed_json


def all_movies():
    parameters = {}
    url=commons.generateApiQuery("radarr", "movie", parameters)
    
    req = get_req(url)
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
    req = get_req(commons.generateApiQuery("radarr", "qualityProfile", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json


def getTags():
    parameters = {}
    req = get_req(commons.generateApiQuery("radarr", "tag", parameters))
    parsed_json = json.loads(req.text)
    return parsed_json


def createTag(tag):
    data_json = {
        "id": max([t["id"] for t in getTags()])+1,
        "label": str(tag)
    }
    add = post_req(commons.generateApiQuery("radarr", "tag"), json=data_json, headers={'Content-Type': 'application/json'})
    if add.status_code == 200:
        return True
    else:
        return False


def getDbIdFromImdbId(tmdbId):
    req = get_req(commons.generateApiQuery("radarr", "movie", {}))
    parsed_json = json.loads(req.text)
    dbId = [f["id"] for f in parsed_json if f["tmdbId"] == tmdbId]
    return dbId[0]

# re route the requests through common
def get_req(app,url,**kwargs):
    app = "radarr"
    req = commons.get_req(app,url,auth=my_auth,**kwargs)
    return req

def delete_req(app,url,**kwargs):
    app = "radarr"
    req = commons.delete_req(app,url,auth=my_auth,**kwargs)
    return req

def post_req(app,url,**kwargs):
    app = "radarr"
    req = commons.post_req(app,url,auth=my_auth,**kwargs)
    return req
