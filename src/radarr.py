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

radarr_config = config["radarr"] if isinstance(config["radarr"]["instances"], list) else [config["radarr"]["instances"]]

addMovieNeededFields = ["tmdbId", "year", "title", "titleSlug", "images"]

def setInstance(label):
    global radarr_config
    radarr_instances = config['radarr']['instances']
    commons.setInstanceName(label)

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


def getAllMedia():
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
        "label": str(tag)
    }
    add = requests.post(commons.generateApiQuery("radarr", "tag"), json=data_json, headers={'Content-Type': 'application/json'})
    response_content = json.loads(add.content.decode('utf-8'))
    if add.status_code == 200 or add.status_code == 201:
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

def notificationProfileExist(chatid):
    # check if profile exists
    profiles = requests.get(commons.generateApiQuery("radarr", "notification"))
    response_content = json.loads(profiles.content.decode('utf-8'))
    profileExists = any(str(chatid) in item['name'] for item in response_content)
    if profileExists: 
        label = getInstance()["label"]
        logger.debug(f'Notification Profile for user {chatid} already exists in instance {label}')
        return True
    else:
        return False

def createNotificationProfile(profileName, chatid):
    bot_token = config["telegram"]["token"]
    # check if user tag exists
    logger.debug(f'Check if user tag exists: {chatid}')
    tag_id = tagExists(chatid)

    if tag_id is None or tag_id == -1:
        # create the tag first
        logger.debug(f'Creating user tag: {chatid}')
        tag_id = createTag(chatid)
        logger.debug(f'Tag created with ID: {tag_id}')

    if notificationProfileExist(chatid):
        return True

    data_json = {
            "name": str(profileName),
            "implementation": "Telegram",
            "isEnabled": False,
            "configContract": "TelegramSettings",
            "fields": [
                  {
                    "order": 0,
                    "name": "botToken",
                    "label": "Bot Token",
                    "helpLink": "https://core.telegram.org/bots",
                    "type": "textbox",
                    "advanced": False,
                    "privacy": "apiKey",
                    "isFloat": False,
                    "value": str(bot_token)
                  },
                  {
                    "order": 1,
                    "name": "chatId",
                    "label": "Chat ID",
                    "helpText": "You must start a conversation with the bot or add it to your group to receive messages",
                    "helpLink": "http://stackoverflow.com/a/37396871/882971",
                    "type": "textbox",
                    "advanced": False,
                    "privacy": "normal",
                    "isFloat": False,
                    "value": str(chatid)
                  },
                  {
                    "order": 2,
                    "name": "topicId",
                    "label": "Topic ID",
                    "helpText": "Specify a Topic ID to send notifications to that topic. Leave blank to use the general topic (Supergroups only)",
                    "helpLink": "https://stackoverflow.com/a/75178418",
                    "type": "textbox",
                    "advanced": False,
                    "privacy": "normal",
                    "isFloat": False
                  },
                  {
                    "order": 3,
                    "name": "sendSilently",
                    "label": "Send Silently",
                    "helpText": "Sends the message silently. Users will receive a notification with no sound",
                    "value": False,
                    "type": "checkbox",
                    "advanced": False,
                    "privacy": "normal",
                    "isFloat": False
                  },
                  {
                    "order": 4,
                    "name": "includeAppNameInTitle",
                    "label": "Include Radarr in Title",
                    "helpText": "Optionally prefix message title with Radarr to differentiate notifications from different applications",
                    "value": False,
                    "type": "checkbox",
                    "advanced": False,
                    "privacy": "normal",
                    "isFloat": False
                  }
                ],
            "tags": [tag_id],
            "onGrab": False,
            "onDownload": True,
            "onUpgrade": True,
            "onRename": False,
            "onMovieAdded": False,
            "onMovieDelete": False,
            "onMovieFileDelete": False,
            "onMovieFileDeleteForUpgrade": False,
            "onHealthIssue": False,
            "onHealthRestored": False,
            "onApplicationUpdate": False,
            "onManualInteractionRequired": False,
            "supportsOnGrab": False,
            "supportsOnDownload": True,
            "supportsOnUpgrade": True,
            "supportsOnRename": False,
            "supportsOnMovieAdded": False,
            "supportsOnMovieDelete": False,
            "supportsOnMovieFileDelete": False,
            "supportsOnMovieFileDeleteForUpgrade": False,
            "supportsOnHealthIssue": False,
            "supportsOnHealthRestored": False,
            "supportsOnApplicationUpdate": False,
            "supportsOnManualInteractionRequired": False,
            "includeHealthWarnings": False
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    add = requests.post(commons.generateApiQuery("radarr", "notification"), json=data_json, headers=headers)

    if add.status_code == 201:
        return True
    else:
        return False