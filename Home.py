import Auth
import os
import gns_util

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class Home(webapp.RequestHandler):
  @Auth.authenticated
  def get(self):
    template_values = {
      'user': Auth.AuthenticatedUser(self.request),
      }
    path = os.path.join(os.path.dirname(__file__), 'templates/home.html')
    gns_util.writeTemplate(self, path, template_values)
  

# ----- mainline ----- #
   
application = webapp.WSGIApplication([
                                      ('/', Home),
                                      ],
                                   debug=True)  
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
  