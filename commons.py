import yaml
import logging

from definitions import CONFIG_PATH, LANG_PATH


log = logging
config = yaml.safe_load(open(CONFIG_PATH, encoding='utf8'))
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='telegramBot.log',
                        filemode='w',
                        level=logging.INFO)

def generateServerAddr(app):
    try:
        if config[app]['server']['ssl']:
            http = 'https://'
        else:
            http = 'http://'
        try:
            addr = config[app]['server']['addr']
            port = config[app]['server']['port']
            return http + addr + ":" + str(port)
        except:
            log.warn("No ip or port defined.")
            
    except:
        log.warn("Generate of serveraddress failed.")

def cleanUrl(text):
    url = text.replace(' ', '%20')
    return url

def generateApiQuery(app, endpoint, parameters={}):
    try:
        apikey = config[app]['auth']['apikey']
        url = generateServerAddr(app) + '/api/' + str(endpoint) + '?apikey=' + str(apikey)
        # If parameters exist iterate through dict and add parameters to URL.
        if parameters:
            for key, value in parameters.items():
                url += '&' + key + '=' + value
        return cleanUrl(url) # Clean URL (validate) and return as string
    except:
        log.warn("Generate of APIQUERY failed.")
