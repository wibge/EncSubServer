import Auth
import gns_util
import logging
import models
import os

from gns_response_codes import *
from django.utils import simplejson

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class MyDevices(webapp.RequestHandler):
  """Request handler for /devices/myDevices."""

  @Auth.authenticated
  def get(self):
    user = Auth.AuthenticatedUser(self.request)
    devices = models.Device.gql("WHERE user = :1", user).fetch(10)
    template_values = {
      'user': user,
      'devices': devices,
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/myDevices.html')
    gns_util.writeTemplate(self, path, template_values)
    

class DeleteDevice(webapp.RequestHandler):
  """Request handler for /devices/delete."""

  def post(self):  
    (user, device) = gns_util.getUserFromRequest(self.request)
    responseDict = {}

    if not user:
      responseDict["code"] = USER_NOT_FOUND
      self.response.out.write(simplejson.dumps(responseDict))
      return

    if user.password != gns_util.crypt(self.request.get('password')):
      responseDict["code"] = PASSWORD_INCORRECT
      self.response.out.write(simplejson.dumps(responseDict))
      return

    device = gns_util.getDevice(self.request.get('udid'), self.request.get('appName')) 
    if device:
      # device exists and it's ours, so delete it
      device.delete()
    else: 
      logging.error('User ID %s cannot delete device [%s]', user.id(), device)
    
    self.response.out.write("success")

  
  @Auth.authenticated
  def get(self):  
    user = Auth.AuthenticatedUser(self.request)
    udid = self.request.get('udid')
    # we check both user and udid, to prevent someone from deleting
    # a UDID they don't own
    device = models.Device.gql("WHERE user = :1 AND udid = :2", user, udid).get()

    if device:
      # device exists and it's ours, so delete it
      device.delete()
    else: 
      logging.error('User ID %s cannot delete device [%s]', user.id(), device)

    self.redirect('/devices/myDevices')      


# ----- mainline ----- #

application = webapp.WSGIApplication([
                                      ('/devices/delete', DeleteDevice),
                                      ('/devices/myDevices', MyDevices),
                                      ],
                                   debug=True)  
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
