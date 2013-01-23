import datetime
import hashlib
import os 
import random
import string
import time

import models

from app_config import CONFIG
from django.utils import simplejson
from gns_response_codes import *
from google.appengine.api import mail
from google.appengine.ext.webapp import template

def writeTemplate(requestHandler, path, dict):
  if not dict:
    dict = {}
  dict['config'] = CONFIG
  dict['STATIC_URL'] = '/static/'
  requestHandler.response.out.write(template.render(path, dict))

def getUserFromRequest(request):
  """Get the user from the request.
	
	Returns:
		(user, device)
  """
  id = request.get('id')
  email = request.get('email')
  udid = request.get('udid')
  appcode = request.get('appcode')
  user = None
  device = None
  
  if id:
    user = models.User.get_by_id(long(id))
  else:
    # TODO : do we really need to check in series like this?
    if email:
      user = models.User.gql("WHERE email = :1", email).get()
    if not user and udid:
      device = getDevice(udid, appcode)
      if device:
        user = device.user
  return (user, device)


def getSubscriptionPlanEndDate(startTime, subscription):
  """Get the subscription plan end date for the given start time and subscription.
	
	Returns: datetime.datetime
  """
  t = startTime.timetuple()
  days = t.tm_mday
  months = t.tm_mon
  years = t.tm_year
 
  if subscription.time_unit == models.SUBSCRIPTION_TIME_UNIT.DAY:
    days += subscription.time_unit_quantity
  elif subscription.time_unit == models.SUBSCRIPTION_TIME_UNIT.MONTH:
    months += subscription.time_unit_quantity  
  elif subscription.time_unit == models.SUBSCRIPTION_TIME_UNIT.YEAR:
    years += subscription.time_unit_quantity
  
  newtuple = (years, months, days, t.tm_hour, t.tm_min, t.tm_sec, 0, 0, t.tm_isdst)
  return datetime.datetime.fromtimestamp(time.mktime(newtuple))
  

def writeUserOnlyPage(user, appcode=CONFIG['default_appcode']):
  """Returns simple HTML page with just the user."""
  return "<html><body>" + writeUser(user) + "</body></html>"

def getDevice(udid, appname):
  if not appname:
    appname = CONFIG['default_appcode']
    
  device = models.Device.gql("WHERE udid = :1 and appname = :2", udid, appname).get()
  if not device and appname == CONFIG['default_appcode']:
    device = models.Device.gql("WHERE udid = :1", udid).get()
    if device and device.appname:
      return None
    
  return device
  
def writeUser(user, appcode=CONFIG['default_appcode']):
  """Returns HTML for a description of the given user.
	
	Returns:
		HTML string.
  """
  t = {'user':user, 'subscriptions': user.subscription_set, 'devices': user.device_set, 'currentsub':user.currentSubscription(appcode)}
  path = os.path.join(os.path.dirname(__file__), 'templates/user_status.html')
  return template.render(path, t)  


def generateCode(length):
  """Generate a random code of the given length.
	
	Returns:
		a string
  """
  return ''.join(random.choice(string.ascii_uppercase) for x in range(length))

  
def createUserResponseDict(user, app):
  """Create a response dict for the given user.
	
	Returns:
		dict
  """
  if not app:
    app = 'efb'
  subscription = user.currentSubscription(app)
  responseDict = {}
 
  #TODO Change back when done testing
  usedTrial = 0
  if user.usedtrial:
    usedTrial = 1
  responseDict["user"] = {"email": user.email, "usedtrial":usedTrial}
  responseDict["code"] = SUCCESS
  if subscription:
    responseDict["subscription"] = subscription.getDict()
  else:
    lastSubscription = user.lastSubscription(app)
    if lastSubscription:
      responseDict['last_subscription'] = lastSubscription.getDict()

  other_subs = user.otherSubscriptions(app)
  responseDict['other_subscriptions'] = [s.getDict() for s in other_subs]

  return responseDict
 

def handleErrorPurchasing(code, msg, request):
  """Handle a purchasing error.
	
	Sends an email and dumps the error.
	
	Returns:
		dict of error code, message, and current time.
  """
  #replymessage = mail.EmailMessage(sender="wibge@gmail.com")
  #replymessage.to = "wibge@gmail.com"
  #replymessage.html = str(msg) + " " + str(code) + " " + "<br>" + str(request) + "<br>" + str(datetime.datetime.today())
  #replymessage.subject = "Error Purchasing"
  #replymessage.send()

  errorDict = {}
  errorDict['code'] = code
  errorDict['msg'] = msg
  errorDict['datetime'] = str(datetime.datetime.today())
  return simplejson.dumps(errorDict)
    

def addSubscriptionPlanToUser(user, subscriptionPlan, itunesReceipt, giftcode):
  """Add a subscription plan for the given user.
	
  Returns:
    new Subscription object
  """
  sub = models.Subscription()
  sub.user = user
  sub.subscriptionPlan = subscriptionPlan
  sub.giftcode = giftcode
  sub.itunesReceipt = itunesReceipt
  sub.appname = subscriptionPlan.appname
  
  sub.trial = False
  if subscriptionPlan.identifier == CONFIG['free_trial_identifier']:
    sub.trial = True
    
  lastSub = user.lastSubscription(sub.appname)
  
  now = datetime.datetime.now()
  if subscriptionPlan.dataset == CONFIG['default_dataset'] and lastSub and lastSub.endDate > now:
    if lastSub.trial:
      lastSub.endDate = now
      lastSub.save()
    sub.startDate = lastSub.endDate
  else:
    sub.startDate = now
  
  
  if itunesReceipt and not subscriptionPlan.nonautorenewing:
    # it's an apple auto renewing subscription
    sub.startDate = datetime.datetime.strptime(itunesReceipt.purchase_date, '%Y-%m-%d %H:%M:%S Etc/%Z')
    sub.endDate = itunesReceipt.expires_date
  else:
    sub.endDate = getSubscriptionPlanEndDate(sub.startDate, subscriptionPlan)
  
  if giftcode:
    giftcode.used = True
    giftcode.email = user.email
    giftcode.save()
  sub.save()
  
  return sub
  

def crypt(text):
  """Crypt the given text."""
  return md5Hash(text)


def md5Hash(text):
    """Generate a md5 hash with the given text"""
    return hashlib.md5(text).hexdigest()

