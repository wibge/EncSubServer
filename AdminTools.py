import datetime
import gns_util
import hashlib
import logging
import models
import re
import sys
import time
import traceback
import urllib
import os
from django.utils import simplejson  
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from app_config import *


class InitializeDatabase(webapp.RequestHandler):
  """Handler that initializes the database."""
  def initENCSubs(self): 
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 1
    sub.name = "1 Month Trial"
    sub.description = "One Month Trial access to the app"
    sub.identifier = "1MONTHTRIAL"
    sub.appname = "enc"
    sub.dataset = "noaa"
    sub.save()
    
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.YEAR
    sub.time_unit_quantity = 1
    sub.name = "1 Year Subscription"
    sub.description = "1 year Apple in app purchase"
    sub.identifier = "1YEARAPPLE"
    sub.valid = True
    sub.appname = "enc"
    sub.appStoreProductID = "ENC1YearUS"
    sub.dataset = "noaa"
    sub.save()
    
    
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 6
    sub.name = "6 Month Subscription"
    sub.description = "6 month gift access to the app"
    sub.identifier = "6MONTHGIFT"
    sub.appname = "enc"
    sub.dataset = "noaa"
    sub.save()
    
    user = models.User()
    user.email = "aaa"
    user.password = "aaa"
    user.save()
  
    user2 = models.User()
    user2.email = "a"
    user2.password = "a"
    user2.save()

    device = models.Device()
    device.udid = "aji"
    device.model = "ipad 2"
    device.user = user
    device.save()
  
    device = models.Device()
    device.udid = "tenuki"
    device.model = "ipad wifi"
    device.user = user
    device.save()
  
  def initGaiaSubs(self): 
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 1
    sub.name = "1 Month Trial"
    sub.description = "One Month Trial access to the app"
    sub.identifier = "1MONTHTRIAL"
    sub.appname = "gaia"
    sub.dataset = "gaiagreen"
    sub.valid = True
    sub.provider = "gift"
    sub.trial = True
    sub.save()

    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.YEAR
    sub.time_unit_quantity = 1
    sub.name = "1 Year Subscription"
    sub.description = "1 year Apple in app purchase"
    sub.identifier = "1YEARAPPLE"
    sub.valid = True
    sub.appname = "gaia"
    sub.appStoreProductID = "GaiaGreen1YearNonAutoRenew"
    sub.provider = "apple"
    sub.dataset = "gaiagreen"
    sub.nonautorenewing = True
    sub.save()

    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 1
    sub.name = "1 Month Subscription"
    sub.description = "1 Month Apple in app purchase"
    sub.identifier = "1MONTHAPPLE"
    sub.valid = True
    sub.appname = "gaia"
    sub.appStoreProductID = "GaiaGreen1Month"
    sub.provider = "apple"
    sub.dataset = "gaiagreen"
    sub.nonautorenewing = True
    sub.save()

    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.YEAR
    sub.time_unit_quantity = 1
    sub.name = "OTMUpgrade"
    sub.description = "Upgrade from OTM to Gaia GPS"
    sub.identifier = "GaiaGPSUpgrade"
    sub.valid = True
    sub.appname = "otm"
    sub.appStoreProductID = "GaiaGPSUpgrade"
    sub.provider = "apple"
    sub.dataset = "gaiagreen"
    sub.nonautorenewing = True
    sub.save()

    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 6
    sub.name = "6 Month Gift"
    sub.description = "6 month gift access to the app"
    sub.identifier = "6MONTHGIFT"
    sub.valid = True
    sub.appname = "gaia"
    sub.dataset = "gaiagreen"
    sub.provider = "gift"
    sub.save()

    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.YEAR
    sub.time_unit_quantity = 1
    sub.name = "1 Year Subscription"
    sub.description = "1 year Apple in app purchase"
    sub.identifier = "1YEARAPPLE"
    sub.valid = True
    sub.appname = "otm"
    sub.appStoreProductID = "GaiaGreen1YearOTM"
    sub.provider = "apple"
    sub.dataset = "gaiagreen"
    sub.nonautorenewing = True
    sub.save()

    
  def get(self):
    # TODO: commented out since we're now live
    self.response.out.write("Deleteing all database records<br />\n\n")
    deleteAll()
    self.response.out.write("Inited test database: ")
    self.response.out.write(CONFIG['default_appcode'])
    
    subtest = models.SubscriptionPlan.gql("WHERE identifier = :1", CONFIG['free_trial_identifier']).get()
    if subtest:
      return
    #urls = [
    #      "register/addUser?email=wibge@gmail.com&password=cookie&udid=tenuki&model=ipad",
    #      "register/addUser?email=andrew@gaiagps.com&password=cookie&udid=clarabelle&model=ipad",
    #      "register/addDevice?email=wibge@gmail.com&password=cookie&udid=aji&model=iphone3g"]


    if CONFIG['default_appcode'] == 'enc':
      self.initENCSubs()
      return
      
    if CONFIG['default_appcode'] == 'gaia':
      self.initGaiaSubs()
      return
      
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 2
    sub.name = "2 Month Trial"
    sub.description = "2 Month Trial access to the app"
    sub.identifier = "2MONTHTRIAL"
    sub.appname = "efb"
    sub.dataset = "faa"
    sub.save()
  
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 6
    sub.name = "6 Month Subscription"
    sub.description = "6 month gift access to the app"
    sub.identifier = "6MONTHGIFT"
    sub.appname = "efb"
    sub.dataset = "faa"
    sub.save()
    
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.YEAR
    sub.time_unit_quantity = 1
    sub.name = "1 Year Subscription"
    sub.description = "1 year Apple in app purchase"
    sub.identifier = "1YEARAPPLE"
    sub.valid = True
    sub.appname = "efb"
    sub.appStoreProductID = "EFB1YearUS"
    sub.dataset = "faa"
    sub.save()
    
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.MONTH
    sub.time_unit_quantity = 1
    sub.name = "1 Month Subscription"
    sub.description = "1 Month Apple in app purchase"
    sub.valid = True
    sub.identifier = "1MONTHAPPLE"
    sub.appname = "efb"
    sub.appStoreProductID = "EFB1MonthUS"
    sub.dataset = "faa"
    sub.save()
     
    
    sub = models.SubscriptionPlan()
    sub.time_unit = models.SUBSCRIPTION_TIME_UNIT.DAY
    sub.time_unit_quantity = 7
    sub.name = "7 Day Subscription"
    sub.description = "7 Day gift access to the app"
    sub.identifier = "7DAYGIFT"
    sub.appname = "efb"
    sub.dataset = "faa"
    sub.save()
    
    return

    user = models.User()
    user.email = "aaa"
    user.password = "aaa"
    user.save()
  
    user2 = models.User()
    user2.email = "a"
    user2.password = "a"
    user2.save()

    device = models.Device()
    device.udid = "aji"
    device.model = "ipad 2"
    device.user = user
    device.save()
  
    device = models.Device()
    device.udid = "5d72899da24f658e971b158dc31e39e35a14fb62"
    device.model = "ipad wifi"
    device.user = user
    device.save()
  
    device = models.Device()
    device.udid = "dbc1e87279c584f0ae86ec16acced7785bd7e8cd"
    device.model = "ipad 2"
    device.user = user2
    device.save()
  
    self.response.out.write("Inited test database")

class CreateGiftCode(webapp.RequestHandler):
  """Handler to create a gift code for the current user."""

  def get(self): 
    self.response.out.write(self.giftCodeCreationPage(""))

  def giftCodeCreationPage(self, message):

    template_values = {
          'subscriptionPlans': models.SubscriptionPlan.gql("WHERE provider='gift'").fetch(1000),
          'message':message
    }

    path = os.path.join(os.path.dirname(__file__), 'templates/create_gift_code.html')
    return template.render(path, template_values)
    
  def post(self):
    subPlanIdentifier = self.request.get('subplan')
    subPlan = None
    message = ""
    email = self.request.get('email')
    gcCount = int(self.request.get('count'))
    if gcCount > 100:
      self.response.out.write("Make fewer than 100")
      return
    if subPlanIdentifier:
      subPlan = models.SubscriptionPlan.gql('WHERE identifier = :1', subPlanIdentifier).get()
    if not subPlan:
      message = 'Subscription plan not found %s' % subPlanIdentifier
  
    response = "Gift codes for subscription %s<br>" % subPlan.name
    if not message:
      i = 0
      while i < gcCount:
        gc = models.Giftcode()
        gc.email = email
        gc.subscriptionPlan = subPlan
        gc.used = False
        gc.giftedBy = users.get_current_user().nickname()
        gc.code = gns_util.generateCode(8)
        gc.save()
        
        response += "%s<br>" % gc.code
        i += 1
        
    
      message = response
  
    self.response.out.write(self.giftCodeCreationPage(message))
    return

  
class DisplayUserPurchases(webapp.RequestHandler):
  """Handler that shows all purchases for the current user."""
  def get(self):
    (user, device) = gns_util.getUserFromRequest(self.request)
    if not user:
        self.response.out.write({"code": USER_NOT_FOUND})
        return

    purchases = user.subscription_plans_set
    response = "<html><body><ul>"
    response += gns_util.writeUser(user)
   
    self.response.out.write(response)


class ShowAll(webapp.RequestHandler):
  def get(self):
    users = models.User.all().fetch(1000)
    response = "<html><body><ul>"
    for user in users:
      response += "<li>" + gns_util.writeUser(user) + "</li>"
    
    response += "</ul><b>Unused Gift Codes</b><ul>"
    for giftcode in models.Giftcode.gql("WHERE used = False").fetch(1000):
      try:
        response += "<li>%s from:%s %s</li>" % (giftcode.subscriptionPlan.identifier, giftcode.giftedBy, giftcode.code)
      except:
        pass

    response += "</ul><b>Used Gift Codes</b><ul>"
    for giftcode in models.Giftcode.gql("WHERE used = True").fetch(1000):
      try:
        response += "<li>%s from:%s to:%s %s</li>" % (giftcode.subscriptionPlan.identifier, giftcode.giftedBy, giftcode.email, giftcode.code)
      except:
        pass

    response += "</ul><b>Subscription Plans</b><ul>"
    for sub in models.SubscriptionPlan.all().fetch(1000):
      response += "<li>%s %s %d %s</li>" % (sub.identifier, sub.name, sub.time_unit, sub.description)
    response += "</ul></body></html>"
    self.response.out.write(response)


def deleteAll(): 
  """Delete all data."""
  # TODO: just return, since we're now live
  return
  db.delete(models.User.all())
  db.delete(models.Device.all())
  db.delete(models.Plate.all())
  db.delete(models.Subscription.all())
  db.delete(models.SubscriptionPlan.all())
  db.delete(models.PasswordChangeToken.all())
  db.delete(models.Giftcode.all())
  db.delete(models.ItunesReceipt.all())
  

class DeleteAll(webapp.RequestHandler):
  """Handler that calls deleteAll()."""
  def get(self):
    deleteAll()
    self.response.out.write("deleted all tables")

  
# ----- mainline ----- #
   
application = webapp.WSGIApplication([
                                      #('/admin/deleteAll', DeleteAll),
                                      ('/admin/init', InitializeDatabase),
                                      ('/admin/giftcode', CreateGiftCode),
                                      ('/admin/show', ShowAll),
                                      ('/admin/showPurchases', DisplayUserPurchases)],
                                   debug=True)  
def main():
  #x = FetchMetarData()
  #x.get()
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
  



