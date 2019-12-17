import requests, json, sys, logging
import commons as commons
import yaml #pip install pyyaml

log = logging
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='telegramBot.log',
                        filemode='w',
                        level=logging.INFO)

addSerieNeededFields = ['tvdbId', 'tvTageId', 'title', 'titleSlug', 'images', 'seasons']
                          

def search(title): 
    parameters = {
        "term": title
    }
    req = requests.get(commons.generateApiQuery('sonarr', 'series/lookup', parameters))
    parsed_json = json.loads(req.text)

    if req.status_code == 200:
        return parsed_json
    else:
        return False

def giveTitles(parsed_json):
    data = []
    for show in parsed_json:
        if all(x in show for x in ['title', 'seasonCount', 'remotePoster', 'year', 'tvdbId']):
            data.append({
                'title': show['title'],
                'seasonCount': show['seasonCount'],
                'poster': show['remotePoster'],
                'year': show['year'],
                'id': show['tvdbId']
            })
    return data

def returnVal(rawjson):
    totalData = []
    seriesList = rawjson
    for show in seriesList:
        specShow = seriesList[show]
        totalData.append(specShow["title"], specShow["itvDb"], specShow["remotePoster"], specShow["seasonCount"], specShow["year"]) 
    return totalData

def inLibrary(tvdbId):
    parameters = {}
    req = requests.get(commons.generateApiQuery('sonarr', 'series', parameters))
    parsed_json = json.loads(req.text)
    for show in parsed_json:
        if show['tvdbId'] == tvdbId:
            return True
            break
    return False

def addToLibrary(tvdbId):
    parameters = {
        "term": "tvdb:" + str(tvdbId)
    }
    req = requests.get(commons.generateApiQuery('sonarr', 'series/lookup', parameters))
    parsed_json = json.loads(req.text)
    data = json.dumps(buildData(parsed_json))
    add = requests.post(commons.generateApiQuery('sonarr', 'series'), data=data)
    if add.status_code == 201:
        return True
    else:
        return False

def buildData(json):
    built_data = {
        'qualityProfileId': 1,
        'addOptions': {'ignoreEpisodesWithFiles': 'true',
                        'ignoreEpisodesWithoutFiles': 'false',
                        'searchForMissingEpisodes':'true'},
        'rootFolderPath': '/media/series/',
        'seasonFolder': 'true'                          
        }

    for show in json:
        for key, value in show.items():
            if key in addSerieNeededFields:
                built_data[key] = value
    return built_data




