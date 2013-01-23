import datetime
import gns_util
import hashlib
import logging
import os
import re
import sys
import time
import traceback
import urllib

from cStringIO import StringIO
from django.utils import simplejson
from gns_response_codes import *
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from models import *


# TODO: why is this in Plans.py?
class Tile(webapp.RequestHandler):
  """Handler to show a tile based on the time."""
  def get(self):    
    min = ( time.gmtime().tm_min ) / 5
    self.redirect('/tiles/%d.png' % min)
    

class AddSubscriptionPlan(webapp.RequestHandler):
  """Handler for /addSubscriptionPlan.
  
  /plans/add?time_unit=1&time_unit_quantity=1&name=NavTech+Worldwide&description=Worldwide+coverage&identifier=NAVTECHWORLDWIDE&appname=efb&appStoreProductID=&dataset=faa&provider=chargify&provider_id=14949
  """
  def get(self):
    sub = SubscriptionPlan()
    sub.time_unit = int(self.request.get('time_unit'))
    sub.time_unit_quantity = int(self.request.get('time_unit_quantity'))
    sub.name = self.request.get('name')
    sub.description = self.request.get('description')
    sub.valid = True
    sub.identifier = self.request.get('identifier')
    sub.appname = self.request.get('appname')
    sub.appStoreProductID = self.request.get('appStoreProductID')
    sub.dataset = self.request.get('dataset')
    sub.provider = self.request.get('provider')
    sub.provider_id = self.request.get('provider_id')
    sub.save()
    self.redirect('/plans/list')


class SetPlanProviderID(webapp.RequestHandler):
  """Handler for /plans/setProviderID.
  
  """
  def get(self):
    identifier = self.request.get('identifier')
    provider_id = self.request.get('provider_id')
    plan = SubscriptionPlan.gql("WHERE identifier = :1", identifier).get()
    if plan:
      plan.provider_id = provider_id
      plan.save()
    self.redirect('/plans/list')


class Plans(webapp.RequestHandler):
  """Handler to show SubscriptionPlans JSON."""
  def get(self):
    provider = self.request.get("p")
    app = self.request.get("app", "")
    plans = []
    if provider == "appstore":
      if app != "":
        plans = SubscriptionPlan.gql("WHERE appStoreProductID != NULL AND appname = :1", app).fetch(10)
      else:
        plans = SubscriptionPlan.gql("WHERE appStoreProductID != NULL").fetch(10)
    else:
      plans = SubscriptionPlan.all()
    responseDict = []
    for plan in plans:
      if plan.appStoreProductID != '':
        responseDict.append(plan.getDict())
    self.response.headers["Content-Type"] = "application/json" 
    self.response.out.write(simplejson.dumps(responseDict))
      
# ----- mainline -----
   
application = webapp.WSGIApplication([
    ('/plans/add', AddSubscriptionPlan),
    ('/plans/list', Plans),
    ('/plans/setProviderID', SetPlanProviderID),
    ('/plans/tile', Tile),
    ],
    debug=True)  

def main():
  #x = FetchMetarData()
  #x.get()
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
  



