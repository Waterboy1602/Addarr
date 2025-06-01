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

sonarr_config = config["sonarr"] if isinstance(config["sonarr"]["instances"], list) else [config["sonarr"]["instances"]]

addSerieNeededFields = ["tvdbId", "tvRageId", "title", "titleSlug", "images", "seasons"]

def setInstance(label):
    global sonarr_config
    sonarr_instances = config['sonarr']['instances']
    commons.setInstanceName(label)

    for instance in sonarr_instances:
        if instance["label"] == label:
            sonarr_config = instance
            logger.info(f"Sonarr instance set to: {label}")
            return

    logger.error(f"Sonarr instance with label '{label}' not found. Default instance will be used.")

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


def getAllMedia():
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
        "label": str(tag)
    }
    add = requests.post(commons.generateApiQuery("sonarr", "tag"), json=data_json, headers={'Content-Type': 'application/json'})
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

def notificationProfileExist(chatid):
    # check if profile exists
    profiles = requests.get(commons.generateApiQuery("sonarr", "notification"))
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
        "onMovieDelete": True,
        "onMovieFileDelete": False,
        "onMovieFileDeleteForUpgrade": True,
        "onHealthIssue": False,
        "onHealthRestored": False,
        "onApplicationUpdate": False,
        "onManualInteractionRequired": False,
        "supportsOnGrab": False,
        "supportsOnDownload": True,
        "supportsOnUpgrade": True,
        "supportsOnRename": False,
        "supportsOnMovieAdded": False,
        "supportsOnMovieDelete": True,
        "supportsOnMovieFileDelete": False,
        "supportsOnMovieFileDeleteForUpgrade": True,
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


    add = requests.post(commons.generateApiQuery("sonarr", "notification"), json=data_json, headers=headers)

    if add.status_code == 201:
        return True
    else:
        return False