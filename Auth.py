import datetime
import gns_util
import logging
import models
import os
import uuid
import gns_util
        
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

COOKIE_TIME_FORMAT = "%a, %d-%b-%Y %H:%M:%S GMT"


def authenticated(fn):
  """Decorator for handler get and post methods.
  
  Usage:
    ...
    @authenticated
    def get(self):
      stuff
    ...
  """
  def wrapper(self):
    # TODO: this may inefficiently cause an additional user lookup
    user = AuthenticatedUser(self.request)
    if user:
      return fn(self)
    else:
      self.redirect('/auth/loginForm?redirect=%s' % self.request.url)
  return wrapper
    

class LoginForm(webapp.RequestHandler):
  def get(self):
    return self.post()

  def post(self):
    args = self.ArgsToDict()
    redirect_url = args.get('redirect', None)
    if redirect_url is not None:
      del(args['redirect'])
    for key in args.iterkeys():
      if redirect_url.find('?') == -1:
        redirect_url += "?"
      else:
        redirect_url += "&"
        redirect_url += "%s=%s" % (key, args[key])

    template_values = {
      'redirect': redirect_url,
      }
    path = os.path.join(os.path.dirname(__file__), 'templates/login.html')
    gns_util.writeTemplate(self, path, template_values)

  def ArgsToDict(self):
    """Converts the URL and POST parameters to a singly-valued dictionary.

    Returns:
      dict with the URL and POST body parameters
    """
    req = self.request
    return dict([(arg, req.get(arg)) for arg in req.arguments()])



class Login(webapp.RequestHandler):   
  """Handler for /auth/login."""
  def get(self):
    return self.post()

  def post(self):
    email = self.request.get('username')
    password = gns_util.crypt(self.request.get('password'))
    redirect = self.request.get('redirect')
    
    user = models.User.gql("WHERE email = :1 AND password = :2", email, password).get()
    if user:
      # User logged in successfully
      session_key = GenerateRandomSessionKey() # generate your session key here
      user.session_key = session_key
      user.put()

      expires_datetime = CookieExpirationDateTime()

      # set cookie as session
      
      self.response.headers.add_header(
        "Set-Cookie", "username=%s; expires=%s; path=/" % (
          user.email, expires_datetime.strftime(COOKIE_TIME_FORMAT)))
      self.response.headers.add_header(
        "Set-Cookie", "session_key=%s; expires=%s; path=/" % (
          user.session_key, expires_datetime.strftime(COOKIE_TIME_FORMAT)))
      
      self.redirect(redirect or '/')      
    else:
      # User login failed
      self.response.out.write("Login failed")
      

def CookieExpirationDateTime():
  """Provide a cookie expiration.
  
  Returns:
    datetime
  """
  # expire the cookie in 30 days
  return datetime.date.today() + datetime.timedelta(30)


def GenerateRandomSessionKey():
  """Provide a session key.
  
  Returns:
    string
  """
  # TODO: this is admittedly a shitty key
  # see: http://stackoverflow.com/questions/817882/unique-session-id-in-python/6092448#6092448
  return str(uuid.uuid1())


def AuthenticatedUser(request):
  """Get the currently authenticated user.
  
  Returns:
    User or None
  """
  email_from_cookie = request.cookies.get("username", "")
  if not email_from_cookie:
    return None
  user = models.User.gql("WHERE email = :1 ", email_from_cookie).get()
  return user


class Logout(webapp.RequestHandler):
  def get(self):
    # remove the cookie
    expires_datetime = datetime.date.today()
    self.response.headers.add_header(
      "Set-Cookie", "username=%s; expires=%s; path=/" % (
        "", expires_datetime.strftime(COOKIE_TIME_FORMAT)))
    self.response.headers.add_header(
      "Set-Cookie", "session_key=%s; expires=%s; path=/" % (
        "", expires_datetime.strftime(COOKIE_TIME_FORMAT)))
    self.redirect("/")
        

# Get the session info from cookie. If the session info match the info stored in datastore
# Then user authenticate successfully.
class TestLogin(webapp.RequestHandler):
  @authenticated
  def get(self):
    # get cookie info
    email_from_cookie = self.request.cookies.get("username", "")

    if email_from_cookie:
      user = models.User.gql("WHERE email = :1 ", email_from_cookie).get()
      if user:
        # the user is logged in correctly
        self.response.out.write("logged in as %s session_key %s" % (user.email, user.session_key))
      else:
        # the user is not logged in
        self.response.out.write("NOPE")
    else:
        # the user is not logged
        self.response.out.write("no email from cookie")


# ----- mainline ----- #

application = webapp.WSGIApplication([
                                      ('/auth/login', Login),
                                      ('/auth/loginForm', LoginForm),
                                      ('/auth/logout', Logout),
                                      ('/auth/show', TestLogin),
                                      ],
                                   debug=True)  
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
  