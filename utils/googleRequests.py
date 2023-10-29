import urllib.request,urllib.parse,urllib.error
import json
import ssl
import logging
from pathlib import Path
from datetime import datetime
from pandas import Timestamp



class googleRequests:
    def __init__(self,serviceURL = None,APIKey = None):
        FILENAME = str(Timestamp(datetime.now()).strftime(format = "%Y-%m-%d %H-%M-%S")) + "-GoogleRequests.log"
        logging.basicConfig(filename=Path('logs',FILENAME).resolve(), level=logging.DEBUG)
        if serviceURL:
            self.serviceURL = serviceURL
        else:
            self.serviceURL = r'https://maps.googleapis.com/maps/api/place/nearbysearch/json?'
        if APIKey:
            self.APIKey = APIKey
        else:
            self.APIKey = r'AIzaSyBjdjvMLuBJYh9wn7erROA-SkCQGsJXjNk'
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    def _createURL(self,lat,long,radius):
        parameters = {}
        parameters['location'] = f"{lat},{long}"
        parameters['radius'] = radius
        parameters['key'] = self.APIKey
        url = self.serviceURL + urllib.parse.urlencode(parameters,safe = ',')
        return url

    def _extractData(self,lat,long,radius):
        url = self._createURL(lat,long,radius)
        output = urllib.request.urlopen(url,context = None)
        jsondata = json.loads(output.read())
        if jsondata['status'] == 'OK':
            if len(jsondata['results']) > 1:    
                return jsondata['results'][1:]
            else:
                logging.warn(f"{lat},{long} : {jsondata['status']}")
                return None
        else:
            logging.warn(f"{lat},{long} : {jsondata['status']}")

