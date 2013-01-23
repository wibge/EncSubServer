import datetime
import gns_util
import logging
import re
import sys
import time
import traceback
import urllib
import os
import Auth

from cStringIO import StringIO
from django.utils import simplejson
from gns_response_codes import *
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from models import *


class ShowAll(webapp.RequestHandler):
  def get(self):
    users = User.all().fetch(1000)
    response = "<html><body><ul>"
    for user in users:
      response += "<li>" + user.email + " - " + str(user.created) + "<ul>"
      devices = user.device_set
      for device in user.device_set:
        response += "<li>%s - %s - %s</li>" % (device.udid, device.model, device.appname)
      response += "</ul></li>"
    response += "</ul></body></html>"
    self.response.out.write(response)
    
    
class DeleteAll(webapp.RequestHandler):
  def get(self):
    db.delete(User.all())
    db.delete(Device.all())
    db.delete(Plate.all())
    db.delete(PasswordChangeToken.all())
    self.response.out.write("deleted all tables")
  

class AddDevice(webapp.RequestHandler):
  def get(self):
    email = self.request.get('email')
    password = gns_util.crypt(self.request.get('password'))
    udid = self.request.get('udid')
    devicetype = self.request.get('model')
    appname = self.request.get('appcode')
    
    acceptPassword = self.request.get('newdevice')
    
    responseDict = {}
    if not email or not password or not udid:
      responseDict["code"] = REQUEST_INVALID
      self.response.out.write(simplejson.dumps(responseDict))
      return
      
    user = User.gql("WHERE email = :1", email).get()
    if not user:
      email = email.lower()
      user = User.gql("WHERE email = :1", email).get()
      if not user:
        responseDict["code"] = USER_NOT_FOUND
        self.response.out.write(simplejson.dumps(responseDict))
        return
      
    if acceptPassword != 'yes' and not user.password == password:
      responseDict["code"] = PASSWORD_INCORRECT
      self.response.out.write(simplejson.dumps(responseDict))
      return
    
    device = gns_util.getDevice(udid, appname)
    if not device:
      device = Device()
      device.udid = udid
      device.model = devicetype
      device.appname = appname
    try:
      if device.user and (device.user != user and device.user.usedtrial):
        user.usedtrial = True
        user.save()
    except:
        device.user = None

    if acceptPassword == 'yes':
      user.password = password
      user.save()
    device.user = user
    device.save()
    
    # set session cookie
    expires_datetime = Auth.CookieExpirationDateTime()      
    self.response.headers.add_header(
      "Set-Cookie", "username=%s; expires=%s; path=/" % (
        user.email, expires_datetime.strftime(Auth.COOKIE_TIME_FORMAT)))
    self.response.headers.add_header(
      "Set-Cookie", "session_key=%s; expires=%s; path=/" % (
        user.session_key, expires_datetime.strftime(Auth.COOKIE_TIME_FORMAT)))

    responseDict = gns_util.createUserResponseDict(device.user, appname)
    self.response.out.write(simplejson.dumps(responseDict))


class RegisterForm(webapp.RequestHandler):
  def get(self):
    return self.post()

  def post(self):
    template_values = {
      'redirect': self.request.get('redirect', '/'),
      }
    path = os.path.join(os.path.dirname(__file__), 'templates/register.html')
    gns_util.writeTemplate(self, path, template_values)


class Register(webapp.RequestHandler):
  def post(self):
    return self.get()

  def get(self):
    email = self.request.get('email')
    password = gns_util.crypt(self.request.get('password'))
    udid = self.request.get('udid')
    devicetype = self.request.get('model')
    appname = self.request.get('appcode')
    redirect = self.request.get('redirect', None)
    responseDict = {}
    if not email or not password:
      responseDict["code"] = REQUEST_INVALID
      self.response.out.write(simplejson.dumps(responseDict))
      return
      
    user = User.gql("WHERE email = :1", email).get()
    if user:
      responseDict["code"] = EMAIL_ALREADY_IN_USE
      self.response.out.write(simplejson.dumps(responseDict))
      return
    else:
      user = User()
      user.email = email
      user.password = password
      session_key = Auth.GenerateRandomSessionKey() # generate your session key here
      user.session_key = session_key
      user.put()
      
      # set session cookie
      expires_datetime = Auth.CookieExpirationDateTime()      
      self.response.headers.add_header(
        "Set-Cookie", "username=%s; expires=%s; path=/" % (
          user.email, expires_datetime.strftime(Auth.COOKIE_TIME_FORMAT)))
      self.response.headers.add_header(
        "Set-Cookie", "session_key=%s; expires=%s; path=/" % (
          user.session_key, expires_datetime.strftime(Auth.COOKIE_TIME_FORMAT)))

      if udid:
        device = gns_util.getDevice(udid, appname)
        if not device:
          device = Device()
          device.udid = udid
          device.model = devicetype
          device.appname = appname
        device.user = user
        device.put()
      
      if redirect:
        return self.redirect(redirect)

      responseDict = gns_util.createUserResponseDict(user, CONFIG['default_appcode'])
      
    self.response.out.write(simplejson.dumps(responseDict))
    

class CheckUDID(webapp.RequestHandler):
  def get(self):
    udid = self.request.get('udid')
    appcode = self.request.get('appcode')
    
    device = gns_util.getDevice(udid, appcode)
  
    if not appcode:
      appcode = CONFIG['default_appcode']
    
    responseDict = {}
    if not device:
      responseDict["code"] = UDID_NOT_FOUND
    else:
      responseDict = gns_util.createUserResponseDict(device.user, appcode)
      
    self.response.out.write(simplejson.dumps(responseDict))
    
    
# ----- mainline ----- #
   
application = webapp.WSGIApplication([('/register/checkUDID', CheckUDID),
                                      ('/register/addUser', Register),
                                      ('/register/form', RegisterForm),
                                      ('/register/addDevice', AddDevice),
#                                      ('/register/deleteAll', DeleteAll),
                                      ('/admin/register/show', ShowAll)],
                                   debug=True)  
def main():
  #x = FetchMetarData()
  #x.get()
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
  



