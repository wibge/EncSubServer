import chargify_util
import datetime
from app_config import CONFIG
from google.appengine.api import datastore
from google.appengine.api import datastore_types
from google.appengine.ext import db

  

class Plate(db.Model):
  updated_date = db.DateProperty()
  effective_date = db.DateProperty()
  cycle = db.StringProperty()
  state = db.StringProperty()
  name = db.StringProperty()
  filename = db.StringProperty()
  airport_code = db.StringProperty()

  
class Chart(db.Model):
  map_type = db.StringProperty()
  name = db.StringProperty()
  updated_date = db.DateProperty()
  effective_date = db.DateProperty()
  expires_date = db.DateProperty()
  
  
class ServerStatus(db.Model):
  plates_updated = db.DateProperty()
  charts_updated = db.DateProperty()
  
  
class User(db.Model):
  email = db.StringProperty()
  password = db.StringProperty()
  u_password = db.StringProperty()
  reset_password_key = db.StringProperty()
  registration_id = db.StringProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  usedtrial = db.BooleanProperty()
  session_key = db.StringProperty()

  def id(self):
    """Delegate to key.id()."""
    return self.key().id()

  def currentSubscription(self, appname, dataset=CONFIG['default_dataset']):
    now = datetime.datetime.now()
    subs = Subscription.gql("WHERE user = :1 and appname = :3 and endDate > :2", self, now, appname).fetch(10)
    for sub in subs:
      if sub.subscriptionPlan.dataset != dataset:
        continue
      if sub.startDate < now:
        return sub
    return None
    
  def lastSubscription(self, appname, dataset=CONFIG['default_dataset']):
    now = datetime.datetime.now()
    subs = Subscription.gql("WHERE user = :1 and appname = :2 ORDER BY endDate DESC", self, appname).fetch(10)
    for sub in subs:
      if sub.subscriptionPlan.dataset != dataset:
        continue
      if sub.startDate < now:
        return sub
    return None
  
  def otherSubscriptions(self, appname):
    """For now, just return any user subscriptions for non-faa datasets."""
    now = datetime.datetime.now()
    subs = Subscription.gql("WHERE user = :1 and appname = :3 and endDate > :2", self, now, appname).fetch(10)
    other = [s for s in subs if s.subscriptionPlan.dataset != CONFIG['default_dataset']]; 
    return other

  def nickname(self):
    return self.email
    
  
class Device(db.Model):
  udid = db.StringProperty()
  model = db.StringProperty()
  last_updated = db.DateProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  user = db.ReferenceProperty(User)
  appname = db.StringProperty()
  
  def __repr__(self):
		return "%s %s %s %s" % (self.udid, self.model, self.created.date(), self.appname)
  

class SUBSCRIPTION_TIME_UNIT:
  DAY, MONTH, YEAR = range(3)

  
class SubscriptionProvider:
  APPSTORE = 'appstore'
  CHARGIFY = 'chargify'
  GIFT = 'gift'


# add fields for subscriptions to specific data sets
class SubscriptionPlan(db.Model):
  time_unit = db.IntegerProperty()
  time_unit_quantity = db.IntegerProperty()
  # TODO: we may need name to be unique, 
  # since we only get a subscription-plan-name back from Spreedly
  name = db.StringProperty()
  description = db.StringProperty()
  appStoreProductID = db.StringProperty()
  valid = db.BooleanProperty()
  identifier = db.StringProperty()
  appname = db.StringProperty()
  dataset = db.StringProperty()
  provider = db.StringProperty()
  provider_id = db.StringProperty()
  trial = db.BooleanProperty()
  nonautorenewing = db.BooleanProperty()
  
  def getDict(self):
    return { 'name':self.name, 'time_unit':str(self.time_unit), 'time_unit_quantity':str(self.time_unit_quantity), 
    'desc':self.description, 'appname': self.appname, 'dataset': self.dataset, 'name':self.name, 'identifier':self.identifier, 'AppleProductID':self.appStoreProductID}

  def isAddOn(self):
    """Whether this plan is an add-on, versus a base subscription."""
    return self.dataset != CONFIG['default_dataset']
  
class PasswordChangeToken(db.Model):
  created = db.DateTimeProperty(auto_now_add=True)
  user = db.ReferenceProperty(User)
  token = db.StringProperty()

  
class ItunesReceipt(db.Model):
  product_id = db.StringProperty()
  transaction_id = db.StringProperty()
  purchase_date = db.StringProperty()
  original_transaction_id = db.StringProperty()
  original_purchase_date = db.StringProperty()
  app_item_id = db.StringProperty()
  version_external_identifier = db.StringProperty()
  bid = db.StringProperty()
  bvrs = db.StringProperty()
  expires_date = db.DateTimeProperty()
  receiptData = db.TextProperty()
  transaction_identifier = db.StringProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  
  
class Giftcode(db.Model):
	created = db.DateTimeProperty(auto_now_add=True)
	expireDate = db.DateTimeProperty()
	subscriptionPlan = db.ReferenceProperty(SubscriptionPlan)
	code = db.StringProperty()
	giftedBy = db.StringProperty()
	used = db.BooleanProperty()
	email = db.StringProperty()
	
	def __repr__(self):
		return "%s %s %d" % (self.code, self.subscriptionPlan.identifier, self.used)
		
		
class Subscription(db.Model):
  created = db.DateTimeProperty(auto_now_add=True)
  user = db.ReferenceProperty(User)
  subscriptionPlan = db.ReferenceProperty(SubscriptionPlan)
  itunesReceipt = db.ReferenceProperty(ItunesReceipt)
  giftcode = db.ReferenceProperty(Giftcode)
  startDate = db.DateTimeProperty()
  endDate = db.DateTimeProperty()
  appname = db.StringProperty()
  trial = db.BooleanProperty()
  provider_id = db.StringProperty()
  canceled = db.BooleanProperty()
  
  def getDict(self):
    plan = self.subscriptionPlan

    responseDict =  {'created': str(self.created.date()), 'startDate': str(self.startDate), 'endDate': str(self.endDate), 
    'desc':plan.description, 'appname': self.appname, 'dataset': plan.dataset, 'name':plan.name, 'trial':self.trial, 'identifier':plan.identifier}
    
    if self.itunesReceipt:
      responseDict['originaltransactionid'] = self.itunesReceipt.original_transaction_id
      responseDict['transactionid'] = self.itunesReceipt.transaction_id
      
    return responseDict
  
  def __repr__(self):
		return "%s %s %s %s %b" % (self.subscriptionPlan.identifier, self.startDate.date(), self.endDate.date(), self.provider_id, self.canceled)
	
  def __str__(self):
 		return "%s %s %s start:%s  end:%s" % (self.subscriptionPlan.name, self.appname, str(self.getDict()), self.startDate.date(), self.endDate.date())

  def isExpired(self):
    """Whether this Subscription is expired."""
    return self.endDate <= datetime.datetime.now()
    
  def expire(self):
    self.endDate = datetime.datetime.now()

  def updateUrl(self):
    if self.subscriptionPlan.provider == SubscriptionProvider.CHARGIFY:
      return chargify_util.generateHostedURL('update_payment', self.provider_id)
    else:
      return None

  def cancelUrl(self):
    if self.subscriptionPlan.provider == SubscriptionProvider.CHARGIFY:
      return '/subs/cancelChargify?sub=%s' % self.key()
    else:
      return None
      
  def reactivateUrl(self):
    if self.subscriptionPlan.provider == SubscriptionProvider.CHARGIFY:
      return '/subs/reactivate?sub=%s' % self.key()
    else:
      return None
  
  
  
  
  
  
  
