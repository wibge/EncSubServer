from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch
import urllib
import re
import sys
import traceback
import datetime
import time
from django.utils import simplejson
from google.appengine.api import memcache
from cStringIO import StringIO
import logging
from models import *
from gns_response_codes import *

      
class AirportListingStatus(webapp.RequestHandler):
  def get(self):
    responseDict = {}
    
    responseDict["date"] = "2011-01-12"
    responseDict["url"] = "http://dl.dropbox.com/u/23335831/Airports.sqlite"
    
    responseDict["force-reset-date"] = "2011-10-25"
    responseDict["new-force-reset-date"] = "2011-10-25"
    responseDict["efb-force-reset-date"] = "2012-06-03"
    responseDict["amb-force-reset-date"] = "2012-03-23"
      
    self.response.out.write(simplejson.dumps(responseDict))
    
   
application = webapp.WSGIApplication([('/airportlistings', AirportListingStatus)],
                                   debug=True)  
def main():
  #x = FetchMetarData()
  #x.get()
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
  



