import Auth
import gns_util
import logging
import os
import time

from models import *

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail

class Email(db.Model):
  created = db.DateTimeProperty(auto_now_add=True)
  subject = db.StringProperty()
  text = db.TextProperty()
  identifier = db.StringProperty()
  
class EmailSent(db.Model):
  email = db.ReferenceProperty(Email)
  subscription = db.ReferenceProperty(Subscription)
  user = db.ReferenceProperty(User)
  sentDate = db.DateTimeProperty(auto_now_add=True)
  
class EmailProcessingStatus(db.Model):
  email = db.ReferenceProperty(Email)
  lastDateProcessed = db.DateTimeProperty()
  count = db.IntegerProperty()
  
def sendEmail(email, user, subscription):
  # swap in personalization
  subject = email.subject
  bodyText = email.text
  bodyText = bodyText.replace("END_DATE", subscription.endDate.strftime("%b %d, %Y"))
  message = mail.EmailMessage(sender=CONFIG['email_address'],
                              subject=subject)

  message.to = user.email
  #message.to = 'wibge@gmail.com'
  message.html = bodyText
  # record it is sent
  message.send()
    
class ContactExpiringSubscriptions(webapp.RequestHandler):
  """Request handler for /devices/myDevices."""

  def get(self):
    
    email = Email.gql("WHERE identifier= :1", "FREETRIALEXPIRED").get()
    status = EmailProcessingStatus.gql("WHERE email = :1", email).get()
    if not status:
      status = EmailProcessingStatus()
      status.count = 0
      status.email = email
      status.lastDateProcessed = datetime.datetime.now() - datetime.timedelta(days=300)
      status.save()
    
    cutoffDate = datetime.datetime.now() + datetime.timedelta(days=2)
    subs = Subscription.gql("WHERE endDate < :1 and endDate > :2 and trial = True ORDER BY endDate ASC", cutoffDate, status.lastDateProcessed).fetch(50)
    if len(subs) == 0:
      return
    responseStr = ""
    numSent = 0
    for sub in subs:
      status.lastDateProcessed = sub.endDate
      currentSub = sub.user.currentSubscription(CONFIG['default_appcode'])
      if currentSub and currentSub.trial != True:
        responseStr += sub.user.email + " has renewed<br>"
        continue
      emailSent = EmailSent.gql("WHERE email = :1 and subscription = :2", email, sub).get()
      if not emailSent:
        emailSent = EmailSent()
        emailSent.user = sub.user
        emailSent.subscription = sub
        emailSent.email = email
        emailSent.save()
        
        sendEmail(email, sub.user, sub)
        responseStr += sub.user.email + "<br>"
        numSent += 1
      else:
        responseStr += sub.user.email + " email already sent<br>"
        
        
        
    status.count += numSent
    status.save()  
    self.response.out.write(responseStr)
    

  
class EditEmail(webapp.RequestHandler):
  def prepareEditingPage(self, email, user, subscription, message):
    template_values = {
      'email': email,
      'user': user,
      'sub': subscription,
      'message': message
    }
    
    path = os.path.join(os.path.dirname(__file__), 'templates/editEmail.html')
    return template.render(path, template_values)
    
  def get(self):
    emailIdentifier = self.request.get('identifier')
    if not emailIdentifier:
      emailIdentifier = 'FREETRIALEXPIRED'
    email = Email.gql('WHERE identifier = :1', emailIdentifier).get()
    
    user = User()
    user.email = 'wibge@gmail.com'
    
    sub = Subscription()
    timestring = "2005-09-01 12:30:09"
    time_format = "%Y-%m-%d %H:%M:%S"
    sub.endDate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(timestring, time_format)))
    
    self.response.out.write(self.prepareEditingPage(email, user, sub, ""))
    
  def post(self):
    emailText = self.request.get('emailText')
    emailIdentifier = self.request.get('identifier')
    emailSubject = self.request.get('subject')
    testOnly = self.request.get('Test')
    
    email = Email.gql('WHERE identifier = :1', emailIdentifier).get()
    if not email:
      return
      
    email.text = emailText
    email.subject = emailSubject
    
    user = User()
    user.email = self.request.get('email')
    
    sub = Subscription()
    timestring = self.request.get('endDate')
    time_format = "%Y-%m-%d %H:%M:%S"
    sub.endDate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(timestring, time_format)))
    
    if testOnly:
      sendEmail(email, user, sub)
    else:
      email.save()
    self.response.out.write(self.prepareEditingPage(email, user, sub, "Email Sent" if testOnly else "Saved"))
    


# ----- mainline ----- #

application = webapp.WSGIApplication([
                                      ('/emailer/expiringSubscriptions', ContactExpiringSubscriptions),
                                      ('/emailer/editEmail', EditEmail)
                                      ],
                                   debug=True)  
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
