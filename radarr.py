#!/usr/bin/env python3

import requests, json, sys, logging
import commons as commons
import yaml

from definitions import CONFIG_PATH, LANG_PATH

log = logging
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='telegramBot.log',
                        filemode='w',
                        level=logging.INFO)

config = yaml.safe_load(open(CONFIG_PATH, encoding='utf8'))
config = config["radarr"]

addMovieNeededFields = ['tmdbId', 'year', 'title', 'titleSlug', 'images']

def search(title): 
    parameters = {
        "term": title
    }
    req = requests.get(commons.generateApiQuery('radarr', 'movie/lookup', parameters))
    parsed_json = json.loads(req.text)

    if req.status_code == 200:
        return parsed_json
    else:
        return False

def giveTitles(parsed_json):
    data = []
    for movie in parsed_json:
        if all(x in movie for x in ['title', 'overview', 'remotePoster', 'year', 'tmdbId']):
            data.append({
                'title': movie['title'],
                'overview': movie['overview'],
                'poster': movie['remotePoster'],
                'year': movie['year'],
                'id': movie['tmdbId']
            })
    return data

def returnVal(rawjson):
    totalData = []
    moviesList = rawjson
    for movie in moviesList:
        specMovie = moviesList[movie]
        totalData.append(specMovie["title"], specMovie["tmdbId"], specMovie["remotePoster"], specMovie["overview"], specMovie["year"]) 
    return totalData

def inLibrary(tmdbId):
    parameters = {}
    req = requests.get(commons.generateApiQuery('radarr', 'movie', parameters))
    parsed_json = json.loads(req.text)
    for movie in parsed_json:
        if movie['tmdbId'] == tmdbId:
            return True
            break
    return False

def addToLibrary(tmdbId):
    parameters = {
        "tmdbId": str(tmdbId)
    }
    req = requests.get(commons.generateApiQuery('radarr', 'movie/lookup/tmdb', parameters))
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json))
    add = requests.post(commons.generateApiQuery('radarr', 'movie'), data=data)
    if add.status_code == 201:
        return True
    else:
        return False

def buildData(json):
    built_data = {
        'qualityProfileId': config["qualityProfileId"],
        'rootFolderPath': config["rootFolder"],
        "addOptions" : {
            "searchForMovie" : config["search"]},
        }

    for key in addMovieNeededFields:
        built_data[key] = json[key]
    return built_data




