import Auth
import datetime
import gns_util
import hashlib
import logging
import models
import os
import re
import sys
import time
import traceback
import urllib
import Auth

from app_config import CONFIG
from cStringIO import StringIO
from django.utils import simplejson
from gns_response_codes import *
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from google.appengine.ext.webapp.util import run_wsgi_app

# looks up the itunes transaction by ID. Adds new UDID to user if the transaction was already used
class UserForTransaction(webapp.RequestHandler):
    """ ??? """
    def get(self):
      (user, device) = gns_util.getUserFromRequest(self.request)
      transactionID = self.request.get('transactionID')
      devicetype = self.request.get('model')
      appname = self.request.get('appcode')
      udid = self.request.get('udid')
      
      receipt = models.ItunesReceipt.gql("WHERE original_transaction_id = :1", transactionID).get()
      if receipt:
        sub = models.Subscription.gql("WHERE itunesReceipt = :1", receipt).get()
        if sub:
          user = sub.user
          device = gns_util.getDevice(udid, appname)
          if not device:
            device = models.Device()
            device.udid = udid
            device.model = devicetype
            device.appname = appname
            
          device.user = user
          device.save()
      
      if user:    
        responseDict = gns_util.createUserResponseDict(user, CONFIG['default_appcode']) 
        self.response.out.write(simplejson.dumps(responseDict))
        return
        
      self.response.out.write(gns_util.handleErrorPurchasing(USER_NOT_FOUND, "user not found", self.request))
      return
  
def itunesReceiptFromDict(receiptResponse, receipt, request, user):
  """ ??? """
  oldReceipt = models.ItunesReceipt.gql("WHERE original_transaction_id = :1 and purchase_date = :2", receiptResponse['original_transaction_id'], receiptResponse['purchase_date']).get()
  if oldReceipt:
    #gns_util.handleErrorPurchasing(RECEIPT_REUSE, "original transactionID has already been processed", request )
    return (oldReceipt, None)
    
  itunesReceipt = models.ItunesReceipt()
  itunesReceipt.product_id = receiptResponse['product_id']
  itunesReceipt.transaction_id = receiptResponse['transaction_id']
  itunesReceipt.purchase_date = receiptResponse['purchase_date']
  itunesReceipt.original_transaction_id = receiptResponse['original_transaction_id']
  itunesReceipt.original_purchase_date = receiptResponse['original_purchase_date']
  itunesReceipt.transaction_identifier = receiptResponse['unique_identifier']
  if 'app_item_id' in receiptResponse:
    itunesReceipt.app_item_id = receiptResponse['app_item_id']
  if 'version_external_identifier' in receiptResponse:
    itunesReceipt.version_external_identifier = receiptResponse['version_external_identifier']
  itunesReceipt.bid = receiptResponse['bid']
  itunesReceipt.bvrs = receiptResponse['bvrs']
  if 'expires_date' in receiptResponse:
    itunesReceipt.expires_date = datetime.datetime.fromtimestamp(int(receiptResponse['expires_date'])/1000)
  itunesReceipt.receiptData = receipt
  itunesReceipt.save()
  
  appStoreProductID = receiptResponse['product_id']
  subscriptionPlan = models.SubscriptionPlan.gql('WHERE appStoreProductID = :1', appStoreProductID).get()
  if not subscriptionPlan:
   #handleErrorPurchasing(INVALID_RECEIPT, "appstore product not found", request)
   return (itunesReceipt, None)

  currentSubscription = user.currentSubscription(subscriptionPlan.appname)
  if currentSubscription and currentSubscription.trial == True:
    currentSubscription.endDate = datetime.datetime.now()
    currentSubscription.save()
    
  sub = gns_util.addSubscriptionPlanToUser(user, subscriptionPlan, itunesReceipt, None)
  
  #sub = models.Subscription()
  #sub.user = user
  #sub.trial = False
  #sub.subscriptionPlan = subscriptionPlan
  #sub.giftcode = None
  #sub.itunesReceipt = itunesReceipt
  #sub.appname = subscriptionPlan.appname
  #sub.startDate = datetime.datetime.strptime(itunesReceipt.purchase_date, '%Y-%m-%d %H:%M:%S Etc/%Z')
  #sub.endDate = itunesReceipt.expires_date  
  #sub.save()
  
  return (itunesReceipt, sub)
  
class AppStorePurchase(webapp.RequestHandler):
  """ ??? """
  def get(self):
    return self.post()
    
  def post(self):
    (user, device) = gns_util.getUserFromRequest(self.request)
    if not user:
      self.response.out.write(gns_util.handleErrorPurchasing(USER_NOT_FOUND, "user not found", self.request))
      return
      
    receipt = self.request.get('receipt')
    if not receipt:
      return self.response.out.write(simplejson.dumps({'code':INVALID_RECEIPT,'message':'No receipt in request'}))
      #receipt = "ewoJInNpZ25hdHVyZSIgPSAiQW0weUdBTXl2bUJsVlZXRDB4aG40aUl2eHlMT05TL2plM1VjWVI0VDRZQU9KU1NUa2hTbHMwUjFkaUU4d2VDNmZxbCtLRmRDSXFLalpuYmozYVczWGJ4S3JETnFHYUVtZ1VxUk90THVjZTVCeVNHZS8wZ0RHZUZCNlAvVWI4RnZyOGlPanhkV24rT1ZlU0lsQ2M0MkYzbmhUK1Z1a29VdzcvM1ZkQytZaFFhQkFBQURWekNDQTFNd2dnSTdvQU1DQVFJQ0NHVVVrVTNaV0FTMU1BMEdDU3FHU0liM0RRRUJCUVVBTUg4eEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUtEQXBCY0hCc1pTQkpibU11TVNZd0pBWURWUVFMREIxQmNIQnNaU0JEWlhKMGFXWnBZMkYwYVc5dUlFRjFkR2h2Y21sMGVURXpNREVHQTFVRUF3d3FRWEJ3YkdVZ2FWUjFibVZ6SUZOMGIzSmxJRU5sY25ScFptbGpZWFJwYjI0Z1FYVjBhRzl5YVhSNU1CNFhEVEE1TURZeE5USXlNRFUxTmxvWERURTBNRFl4TkRJeU1EVTFObG93WkRFak1DRUdBMVVFQXd3YVVIVnlZMmhoYzJWU1pXTmxhWEIwUTJWeWRHbG1hV05oZEdVeEd6QVpCZ05WQkFzTUVrRndjR3hsSUdsVWRXNWxjeUJUZEc5eVpURVRNQkVHQTFVRUNnd0tRWEJ3YkdVZ1NXNWpMakVMTUFrR0ExVUVCaE1DVlZNd2daOHdEUVlKS29aSWh2Y05BUUVCQlFBRGdZMEFNSUdKQW9HQkFNclJqRjJjdDRJclNkaVRDaGFJMGc4cHd2L2NtSHM4cC9Sd1YvcnQvOTFYS1ZoTmw0WElCaW1LalFRTmZnSHNEczZ5anUrK0RyS0pFN3VLc3BoTWRkS1lmRkU1ckdYc0FkQkVqQndSSXhleFRldngzSExFRkdBdDFtb0t4NTA5ZGh4dGlJZERnSnYyWWFWczQ5QjB1SnZOZHk2U01xTk5MSHNETHpEUzlvWkhBZ01CQUFHamNqQndNQXdHQTFVZEV3RUIvd1FDTUFBd0h3WURWUjBqQkJnd0ZvQVVOaDNvNHAyQzBnRVl0VEpyRHRkREM1RllRem93RGdZRFZSMFBBUUgvQkFRREFnZUFNQjBHQTFVZERnUVdCQlNwZzRQeUdVakZQaEpYQ0JUTXphTittVjhrOVRBUUJnb3Foa2lHOTJOa0JnVUJCQUlGQURBTkJna3Foa2lHOXcwQkFRVUZBQU9DQVFFQUVhU2JQanRtTjRDL0lCM1FFcEszMlJ4YWNDRFhkVlhBZVZSZVM1RmFaeGMrdDg4cFFQOTNCaUF4dmRXLzNlVFNNR1k1RmJlQVlMM2V0cVA1Z204d3JGb2pYMGlreVZSU3RRKy9BUTBLRWp0cUIwN2tMczlRVWU4Y3pSOFVHZmRNMUV1bVYvVWd2RGQ0TndOWXhMUU1nNFdUUWZna1FRVnk4R1had1ZIZ2JFL1VDNlk3MDUzcEdYQms1MU5QTTN3b3hoZDNnU1JMdlhqK2xvSHNTdGNURXFlOXBCRHBtRzUrc2s0dHcrR0szR01lRU41LytlMVFUOW5wL0tsMW5qK2FCdzdDMHhzeTBiRm5hQWQxY1NTNnhkb3J5L0NVdk02Z3RLc21uT09kcVRlc2JwMGJzOHNuNldxczBDOWRnY3hSSHVPTVoydG04bnBMVW03YXJnT1N6UT09IjsKCSJwdXJjaGFzZS1pbmZvIiA9ICJld29KSW5GMVlXNTBhWFI1SWlBOUlDSXhJanNLQ1NKd2RYSmphR0Z6WlMxa1lYUmxJaUE5SUNJeU1ERXhMVEEzTFRBeklEQXhPakF4T2pNeklFVjBZeTlIVFZRaU93b0pJbWwwWlcwdGFXUWlJRDBnSWpRME56azJPRFEwT0NJN0Nna2laWGh3YVhKbGN5MWtZWFJsTFdadmNtMWhkSFJsWkNJZ1BTQWlNakF4TVMwd055MHdNeUF3TVRvd05qb3pNeUJGZEdNdlIwMVVJanNLQ1NKbGVIQnBjbVZ6TFdSaGRHVWlJRDBnSWpFek1EazJOVFV4T1RNd01EQWlPd29KSW5CeWIyUjFZM1F0YVdRaUlEMGdJa1ZHUWpGTmIyNTBhRlZUSWpzS0NTSjBjbUZ1YzJGamRHbHZiaTFwWkNJZ1BTQWlNVEF3TURBd01EQXdNekl6TVRVMk5DSTdDZ2tpYjNKcFoybHVZV3d0Y0hWeVkyaGhjMlV0WkdGMFpTSWdQU0FpTWpBeE1TMHdOeTB3TXlBd01EbzFNVG93TnlCRmRHTXZSMDFVSWpzS0NTSnZjbWxuYVc1aGJDMTBjbUZ1YzJGamRHbHZiaTFwWkNJZ1BTQWlNVEF3TURBd01EQXdNekl6TVRRNU15STdDZ2tpWW1sa0lpQTlJQ0pqYjIwdVoyeHZZbUZzYm1GMmMyOTFjbU5sTG1WbVlpSTdDZ2tpWW5aeWN5SWdQU0FpTVM0d0lqc0tmUT09IjsKCSJlbnZpcm9ubWVudCIgPSAiU2FuZGJveCI7CgkicG9kIiA9ICIxMDAiOwoJInNpZ25pbmctc3RhdHVzIiA9ICIwIjsKfQ=="
    
    #receipt = "ewoJInNpZ25hdHVyZSIgPSAiQXJSUW5hQ05majdDUll1V3dNcG1wVDV0Wkd5RFpyYjBCZk1Sakx4Y20xRGhRRHFYWVY2SmJwQ0poU0pjTzlXbkFJcW1TcmFSZ0x5VDJiejhRUCtsbzZQY2JDakV0cm1JRUlVKzliclA0d0pBL2dPbFVRY0QwS2xpZmtpRUs3OXlUQ1BFOHRzbVF1VmpDTlozZmM4a3VIWnhTYmFGMi93L1p0ZGRleU5HdWIxaUFBQURWekNDQTFNd2dnSTdvQU1DQVFJQ0NHVVVrVTNaV0FTMU1BMEdDU3FHU0liM0RRRUJCUVVBTUg4eEN6QUpCZ05WQkFZVEFsVlRNUk13RVFZRFZRUUtEQXBCY0hCc1pTQkpibU11TVNZd0pBWURWUVFMREIxQmNIQnNaU0JEWlhKMGFXWnBZMkYwYVc5dUlFRjFkR2h2Y21sMGVURXpNREVHQTFVRUF3d3FRWEJ3YkdVZ2FWUjFibVZ6SUZOMGIzSmxJRU5sY25ScFptbGpZWFJwYjI0Z1FYVjBhRzl5YVhSNU1CNFhEVEE1TURZeE5USXlNRFUxTmxvWERURTBNRFl4TkRJeU1EVTFObG93WkRFak1DRUdBMVVFQXd3YVVIVnlZMmhoYzJWU1pXTmxhWEIwUTJWeWRHbG1hV05oZEdVeEd6QVpCZ05WQkFzTUVrRndjR3hsSUdsVWRXNWxjeUJUZEc5eVpURVRNQkVHQTFVRUNnd0tRWEJ3YkdVZ1NXNWpMakVMTUFrR0ExVUVCaE1DVlZNd2daOHdEUVlKS29aSWh2Y05BUUVCQlFBRGdZMEFNSUdKQW9HQkFNclJqRjJjdDRJclNkaVRDaGFJMGc4cHd2L2NtSHM4cC9Sd1YvcnQvOTFYS1ZoTmw0WElCaW1LalFRTmZnSHNEczZ5anUrK0RyS0pFN3VLc3BoTWRkS1lmRkU1ckdYc0FkQkVqQndSSXhleFRldngzSExFRkdBdDFtb0t4NTA5ZGh4dGlJZERnSnYyWWFWczQ5QjB1SnZOZHk2U01xTk5MSHNETHpEUzlvWkhBZ01CQUFHamNqQndNQXdHQTFVZEV3RUIvd1FDTUFBd0h3WURWUjBqQkJnd0ZvQVVOaDNvNHAyQzBnRVl0VEpyRHRkREM1RllRem93RGdZRFZSMFBBUUgvQkFRREFnZUFNQjBHQTFVZERnUVdCQlNwZzRQeUdVakZQaEpYQ0JUTXphTittVjhrOVRBUUJnb3Foa2lHOTJOa0JnVUJCQUlGQURBTkJna3Foa2lHOXcwQkFRVUZBQU9DQVFFQUVhU2JQanRtTjRDL0lCM1FFcEszMlJ4YWNDRFhkVlhBZVZSZVM1RmFaeGMrdDg4cFFQOTNCaUF4dmRXLzNlVFNNR1k1RmJlQVlMM2V0cVA1Z204d3JGb2pYMGlreVZSU3RRKy9BUTBLRWp0cUIwN2tMczlRVWU4Y3pSOFVHZmRNMUV1bVYvVWd2RGQ0TndOWXhMUU1nNFdUUWZna1FRVnk4R1had1ZIZ2JFL1VDNlk3MDUzcEdYQms1MU5QTTN3b3hoZDNnU1JMdlhqK2xvSHNTdGNURXFlOXBCRHBtRzUrc2s0dHcrR0szR01lRU41LytlMVFUOW5wL0tsMW5qK2FCdzdDMHhzeTBiRm5hQWQxY1NTNnhkb3J5L0NVdk02Z3RLc21uT09kcVRlc2JwMGJzOHNuNldxczBDOWRnY3hSSHVPTVoydG04bnBMVW03YXJnT1N6UT09IjsKCSJwdXJjaGFzZS1pbmZvIiA9ICJld29KSW1sMFpXMHRhV1FpSUQwZ0lqTTJOall3TWpRd055STdDZ2tpYjNKcFoybHVZV3d0ZEhKaGJuTmhZM1JwYjI0dGFXUWlJRDBnSWpFd01EQXdNREF3TURBek9ESTNOalFpT3dvSkluQjFjbU5vWVhObExXUmhkR1VpSUQwZ0lqSXdNVEF0TURRdE1EZ2dNRFE2TlRNNk1UZ2dSWFJqTDBkTlZDSTdDZ2tpY0hKdlpIVmpkQzFwWkNJZ1BTQWlZMjl0TG1kaGFXRm5jSE11UldGeWRHaE9RMGQxYkdZaU93b0pJblJ5WVc1ellXTjBhVzl1TFdsa0lpQTlJQ0l4TURBd01EQXdNREF3TXpneU56WTBJanNLQ1NKeGRXRnVkR2wwZVNJZ1BTQWlNU0k3Q2draWIzSnBaMmx1WVd3dGNIVnlZMmhoYzJVdFpHRjBaU0lnUFNBaU1qQXhNQzB3TkMwd09DQXdORG8xTXpveE9DQkZkR012UjAxVUlqc0tDU0ppYVdRaUlEMGdJalZhVUU0ek9FYzJSMFV1WTI5dExuUnlZV2xzWW1Wb2FXNWtMa2RoYVdGSFVGTWlPd29KSW1KMmNuTWlJRDBnSWpJdU9UQTBJanNLZlE9PSI7CgkicG9kIiA9ICIxMDAiOwoJInNpZ25pbmctc3RhdHVzIiA9ICIwIjsKfQ=="
    #logging.info(receipt)
    
    receiptDict = {'receipt-data': receipt, 'password':CONFIG['iapp_password']}
    appleResponse = urlfetch.fetch(url='https://buy.itunes.apple.com/verifyReceipt', payload=simplejson.dumps(receiptDict), method=urlfetch.POST, validate_certificate=False)
    appleResponseDict = simplejson.loads(appleResponse.content)
    status = appleResponseDict['status']
    
    if status == 21007:
      # it's a sandbox receipt, send to sandbox server instead
      appleResponse = urlfetch.fetch(url='https://sandbox.itunes.apple.com/verifyReceipt', payload=simplejson.dumps(receiptDict), method=urlfetch.POST, validate_certificate=False)
      appleResponseDict = simplejson.loads(appleResponse.content)
      status = appleResponseDict['status']
      
    if status != 0 and status != 21006:
      self.response.out.write(INVALID_RECEIPT, "Apple server couldn't find receipt %d" % status, self.request)
      return
      
    receiptResponse = appleResponseDict['receipt']
    logging.info("receipt response:%s" % receiptResponse)
   

    (itunesReceipt, sub) = itunesReceiptFromDict(receiptResponse, receipt, self.request, user)
    if 'latest_receipt' in appleResponseDict and 'latest_receipt_info' in appleResponseDict:
      (lastitunesReceipt, sub) = itunesReceiptFromDict(appleResponseDict['latest_receipt_info'], appleResponseDict['latest_receipt'], self.request, user)
    if 'latest_receipt' in appleResponseDict and 'latest_expired_receipt_info' in appleResponseDict:
      (lastitunesReceipt, sub) = itunesReceiptFromDict(appleResponseDict['latest_expired_receipt_info'], appleResponseDict['latest_receipt'], self.request, user)
    
    logging.info("new sub:%s" % sub)
    (user, device) = gns_util.getUserFromRequest(self.request)

    appcode =  CONFIG['default_appcode']
    if sub is not None:
      appcode = sub.appname
      
    responseDict = gns_util.createUserResponseDict(user, appcode)

    #responseDict['appleDict'] = appleResponseDict
    self.response.out.write(simplejson.dumps(responseDict))
    
    if CONFIG['default_appcode'] == 'gaia':
      subject = "New Gaia Green Subscription"
      bodyText = "from user %s" % user.email
      message = mail.EmailMessage(sender=CONFIG['email_address'],
                                  subject=subject)

      message.to = user.email
      message.to = 'gaia@gaiagps.com'
      message.html = bodyText
      # record it is sent
      message.send()
    return 
   

class UserInfo(webapp.RequestHandler):
  """ ??? """
  def get(self):
    (user, device) = gns_util.getUserFromRequest(self.request)
    appcode = self.request.get('appcode')
    if not appcode:
      appcode = CONFIG['default_appcode']
    self.response.out.write(gns_util.writeUserOnlyPage(user, appcode))


class PurchaseGiftSubscription(webapp.RequestHandler):
  def get(self):
    code = self.request.get('giftcode')
    appcode = self.request.get('appcode')
    if not appcode:
      appcode = CONFIG['default_appcode']
    (user, device) = gns_util.getUserFromRequest(self.request)
    
    if not user:
      self.response.out.write(simplejson.dumps({"code":USER_NOT_FOUND}))
      return
    giftcode = models.Giftcode.gql("WHERE code = :1", code).get()
    if not giftcode:
      self.response.out.write(simplejson.dumps({"code":BAD_GIFTCODE}))
      return
      
    if giftcode.used:
      self.response.out.write(simplejson.dumps({"code":BAD_GIFTCODE}))
      return
      
      
    
    subscriptionPlan = giftcode.subscriptionPlan
    
    if subscriptionPlan.appname != appcode:
      self.response.out.write(simplejson.dumps({"code":BAD_GIFTCODE}))
      return
    gns_util.addSubscriptionPlanToUser(user, subscriptionPlan, None, giftcode)
    
    responseDict = gns_util.createUserResponseDict(user, subscriptionPlan.appname)
    
    self.response.out.write(simplejson.dumps(responseDict))
    

class AddFreeTrial(webapp.RequestHandler):
  """ ??? """
  def get(self):
    (user, device) = gns_util.getUserFromRequest(self.request)
    if not user:
      self.response.out.write(simplejson.dumps({"code":USER_NOT_FOUND}))
      return
    if user.usedtrial:
      responseDict = gns_util.createUserResponseDict(user, "efb")
      self.response.out.write(simplejson.dumps(responseDict))
      return
    
    subscriptionPlan = models.SubscriptionPlan.gql("WHERE identifier= :1", CONFIG['free_trial_identifier']).get()
    sub = gns_util.addSubscriptionPlanToUser(user, subscriptionPlan, None, None)
    user.usedtrial = True
    user.save()
    responseDict = gns_util.createUserResponseDict(user, CONFIG['default_appcode'])
    #responseDict['now'] = str(datetime.datetime.now())
    #responseDict['substart'] = str(sub.startDate)
  
    self.response.out.write(simplejson.dumps(responseDict))


class AddFreeTrialOneYear(webapp.RequestHandler):
  """ ??? """
  def get(self):
    (user, device) = gns_util.getUserFromRequest(self.request)
    if not user:
      self.response.out.write(simplejson.dumps({"code": USER_NOT_FOUND}))
      return
    if user.usedtrial:
      responseDict = gns_util.createUserResponseDict(user, CONFIG['default_appcode'])
      self.response.out.write(simplejson.dumps(responseDict))
      return

    subscriptionPlan = models.SubscriptionPlan.gql("WHERE identifier= :1", "ENCUSONEYEARGIFT").get()
    gns_util.addSubscriptionPlanToUser(user, subscriptionPlan, None, None)
    user.usedtrial = True
    user.save()
    responseDict = gns_util.createUserResponseDict(user, CONFIG['default_appcode'])
    #responseDict['now'] = str(datetime.datetime.now())
    #responseDict['substart'] = str(sub.startDate)

    self.response.out.write(simplejson.dumps(responseDict))


class ResetPasswordForm(webapp.RequestHandler):
  """ ??? """
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/reset_password.html')
    gns_util.writeTemplate(self, path, None)


class SendPasswordResetEmail(webapp.RequestHandler):
  """ ??? """
  def send_email(self,email,udid,appcode):
    user = None
    if email:
      user = models.User.gql("WHERE email = :1", email).get()
    if not user and udid:
      device = gns_util.getDevice(udid, appcode)
      if device:
        user = device.user
    if not user:
      self.response.out.write({"code": USER_NOT_FOUND})
      return
      
    token = models.PasswordChangeToken()
    token.user = user
    token.put()   
    token.token = hashlib.sha224(str(token.key())).hexdigest()  
    token.put()
      
    message = mail.EmailMessage(sender=CONFIG['password_reset_email_address'],
                                  subject="%s Password Reset" % CONFIG['appname'])
      
    message.to = user.email
    message.body = """
        Hello,
        
        %(appname)s received a request to reset the password for this email address. To set a new password visit:
        http://%(host)s/user/changePasswordForm?t=%(token)s
        
        
        """  % {'appname':CONFIG['appname'], 'host': CONFIG['host'], 'token': token.token}
      
    message.send()
    path = os.path.join(os.path.dirname(__file__), 'templates/sent_reset_password_email.html')
    gns_util.writeTemplate(self, path, {"email":email})
    
  def get(self):
    email = self.request.get('email')
    udid = self.request.get('udid')
    appcode = self.request.get('appcode')
    self.send_email(email,udid,appcode)

  def post(self):
    email = self.request.get('email')
    udid = None
    appcode = None
    self.send_email(email,udid,appcode)


  
class ChangePassword(webapp.RequestHandler):
  """ ??? """
  def post(self):
    t = self.request.get('t')
    token = models.PasswordChangeToken.gql("WHERE token = :1", t).get()
    
    user = Auth.AuthenticatedUser(self.request)

    if not token and not user:
      path = os.path.join(os.path.dirname(__file__), 'templates/invalid_password.html')
      gns_util.writeTemplate(self, path, None)
    
      return
    
    if token and not user:
      user = token.user

    password = gns_util.crypt(self.request.get('password'))
    password2 = gns_util.crypt(self.request.get('password2'))
    if not password or not password == password2:
      template_values = {
                  'tokenkey': t,
                  'message': "Passwords don't match",
                  'email': user.email
      }

      path = os.path.join(os.path.dirname(__file__), 'templates/change_password.html')
      gns_util.writeTemplate(self, path, template_values)
      
      return 
    
    user.password = password
    user.put()
    
    if token:
      db.delete(token)

    path = os.path.join(os.path.dirname(__file__), 'templates/message.html')
    gns_util.writeTemplate(self, path, {"message":"Password changed"})

      
class ChangePasswordForm(webapp.RequestHandler):
  """ Used for reseting a password from a reset request """
  def get(self):
    t = self.request.get('t')
    token = models.PasswordChangeToken.gql("WHERE token = :1", t).get()

    user = Auth.AuthenticatedUser(self.request)

    if not token and not user:
      path = os.path.join(os.path.dirname(__file__), 'templates/invalid_password.html')
      gns_util.writeTemplate(self, path, None)
      
      return
   
    if token and not user:
      user = token.user

    template_values = {
                'tokenkey': t,
                'email': user.email
    }
      
    path = os.path.join(os.path.dirname(__file__), 'templates/change_password.html')
    gns_util.writeTemplate(self, path, template_values)
    
    

class ChangeEmail(webapp.RequestHandler):
  """ ??? """
  def get(self):
    password = gns_util.crypt(self.request.get('password'))
    udid = self.request.get('udid')
    email = self.request.get('email')
    appcode = self.request.get('appcode')
    responseDict = {}
    if not email:
      responseDict['code'] = EMAIL_INVALID
      self.response.out.write(simplejson.dumps(responseDict))
      return
    device = None
    if udid:
      device = gns_util.getDevice(udid, appcode)
    if not device:
      responseDict['code'] = UDID_NOT_FOUND
      self.response.out.write(simplejson.dumps(responseDict))
      return
    if not device.user.password == password:
      responseDict['code'] = PASSWORD_INCORRECT
      self.response.out.write(simplejson.dumps(responseDict))
      return

    device.user.email = email
    device.user.save()
    
    responseDict = gns_util.createUserResponseDict(device.user, appcode)
    self.response.out.write(simplejson.dumps(responseDict))
    return

class ChangeEmailAndPassword(webapp.RequestHandler):
  """ ??? """
  def get(self):
    password = gns_util.crypt(self.request.get('password'))
    newPassword = gns_util.crypt(self.request.get('newPassword'))
    udid = self.request.get('udid')
    email = self.request.get('email')
    appcode = self.request.get('appcode')
    responseDict = {}
    if not email:
      responseDict['code'] = EMAIL_INVALID
      self.response.out.write(simplejson.dumps(responseDict))
      return
    if not newPassword:
      responseDict['code'] = EMAIL_INVALID
      self.response.out.write(simplejson.dumps(responseDict))
      return
      
    device = None
    if udid:
      device = gns_util.getDevice(udid, appcode)
    if not device:
      responseDict['code'] = UDID_NOT_FOUND
      self.response.out.write(simplejson.dumps(responseDict))
      return
    if not device.user.password == password:
      responseDict['code'] = PASSWORD_INCORRECT
      self.response.out.write(simplejson.dumps(responseDict))
      return

    device.user.email = email
    device.user.password = newPassword
    device.user.save()
    
    expires_datetime = Auth.CookieExpirationDateTime()

    self.response.headers.add_header(
      "Set-Cookie", "username=%s; expires=%s; path=/" % (
        device.user.email, expires_datetime.strftime(Auth.COOKIE_TIME_FORMAT)))
    self.response.headers.add_header(
      "Set-Cookie", "session_key=%s; expires=%s; path=/" % (
        device.user.session_key, expires_datetime.strftime(Auth.COOKIE_TIME_FORMAT)))

    responseDict = gns_util.createUserResponseDict(device.user, appcode)
    self.response.out.write(simplejson.dumps(responseDict))
    return

class CryptPassword(webapp.RequestHandler):
  """Request handler for /cryptPassword.
  
  Crypt a single user's password, identified by email param 
  in the request.
  """
  def get(self):
    email = self.request.get('email', None)
    if not email:
      return
    user = models.User.gql("WHERE email = :1", email).get()
    if not user:
      return
    cryptPasswordForUser(user)
    self.response.out.write(gns_util.writeUserOnlyPage(user))


def cryptPasswordForUser(user):
  """Crypt the password and stash the unencrypted in u_password."""
  if user.u_password:
    # user has already had their password encrypted, so skip
    return
  old_password = user.password
  new_password = gns_util.crypt(old_password)
  user.u_password = old_password
  user.password = new_password
  user.put()


class CryptPasswordsOneByOne(webapp.RequestHandler):
  """Request handler for /cryptPasswords.
  
  Step through all users one by one, crypting passwords.
  """
  def get(self):
    email = self.request.get('email', None)
    if not email:
      # First request, just get the first User out of the datastore.
      user = models.User.gql('ORDER BY email DESC').get()
      email = user.email

    q = models.User.gql('WHERE email <= :1 ORDER BY email DESC', email)
    users = q.fetch(limit=2)
    current_user = users[0]
    if len(users) == 2:
      next_email = users[1].email
      next_url = '/user/cryptPasswordsOneByOne?email=%s' % urllib.quote(next_email)
    else:
      next_email = 'FINISHED'
      next_url = '/'  # Finished processing, go back to main page.

    cryptPasswordForUser(current_user)   

    context = {
        'current_email': email,
        'next_name': next_email,
        'next_url': next_url,
    }
    self.response.out.write(template.render('templates/crypt_passwords.html', context))
    


class CryptPasswords(webapp.RequestHandler):
  """Request handler for /cryptPasswords.
  
  Step through all in blocks on N size, crypting passwords and stashing
  the previous unencrypted password.
  """
  def get(self):
    fetch_block_size = 100
    current_email = self.request.get('email', None)
    if not current_email:
      # First request, just get the first User out of the datastore.
      user = models.User.gql('ORDER BY email DESC').get()
      current_email = user.email

    q = models.User.gql('WHERE email <= :1 ORDER BY email DESC', current_email)
    users = q.fetch(limit=fetch_block_size)
    users_to_crypt = []
    
    if len(users) == fetch_block_size:
      # full block, which means more users to do after this block.
      # Begin the next block with the last user of this block
      next_email = users[-1].email
      next_url = '/user/cryptPasswords?email=%s' % urllib.quote(next_email)
      # process all users but the last in the block; 
      # we'll start with that one in the next run
      users_to_crypt = users[:-1]
    else:
      # partial block, meaning we got all the users
      next_email = 'FINISHED'
      next_url = '/admin/show'  # Finished processing
      # process all the users in the block
      users_to_crypt = users

    for user in users_to_crypt:
      cryptPasswordForUser(user)
    
    context = {
        'fetch_block_size': fetch_block_size,
        'current_email': current_email,
        'next_email': next_email,
        'next_url': next_url,
    }
    self.response.out.write(template.render('templates/crypt_passwords.html', context))


# ----- mainline ----- #

application = webapp.WSGIApplication([
                                      ('/user/appstorepurchase', AppStorePurchase),
                                      ('/user/changeEmail', ChangeEmail),
                                      ('/user/changeEmailAndPassword', ChangeEmailAndPassword),
                                      ('/user/changePassword', ChangePassword),
                                      ('/user/changePasswordForm', ChangePasswordForm),
                                      ('/user/resetPasswordForm', ResetPasswordForm),
                                      ('/user/cryptPassword', CryptPassword),
                                      ('/user/cryptPasswords', CryptPasswords),
                                      ('/user/cryptPasswordsOneByOne', CryptPasswordsOneByOne),
                                      ('/user/freetrial', AddFreeTrial),
                                      ('/user/freeoneyear', AddFreeTrialOneYear),
                                      ('/user/giftPurchase', PurchaseGiftSubscription),
                                      ('/user/passwordReset', SendPasswordResetEmail),
                                      ('/user/show', UserInfo),
                                      ('/user/userFromTransaction', UserForTransaction)
                                      ],
                                   debug=True)  
def main():
  #x = FetchMetarData()
  #x.get()
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
  



