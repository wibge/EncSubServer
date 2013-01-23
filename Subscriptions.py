import Auth
import chargify_util
import datetime
import gns_util
import logging
import models
import os
import urllib

from app_config import CONFIG
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from pychargify.api import *


class ExpiredSubscriptions(webapp.RequestHandler):
  @Auth.authenticated
  def get(self):
    user = Auth.AuthenticatedUser(self.request)
    current_sub = user.currentSubscription(CONFIG['default_appcode'])
    subscription_plans = models.SubscriptionPlan.all().filter(
      'provider =', models.SubscriptionProvider.CHARGIFY).order('name').fetch(10)
      
    # keep only expired subscriptions
    subscriptions = [s for s in user.subscription_set if s.isExpired()]

    template_values = {
      'user': user,
      'subscriptions': subscriptions,
      'request': self.request,
      }
    path = os.path.join(os.path.dirname(__file__), 'templates/expiredSubscriptions.html')
    gns_util.writeTemplate(self, path, template_values)


class MySubscriptions(webapp.RequestHandler):
  @Auth.authenticated
  def get(self):
    
    user = Auth.AuthenticatedUser(self.request)
          
    current_sub = user.currentSubscription('efb')
    subscription_plans = models.SubscriptionPlan.all().filter(
      'provider =', models.SubscriptionProvider.CHARGIFY).order('name').fetch(10)
    subscriptions = user.subscription_set

    # remove expired subscriptions
    subscriptions = [s for s in subscriptions if not s.isExpired()]
    
    # remove any plans we've already bought subscriptions for
    
    # first pass: if we already have a paid-for base faa subscription,
    # then remove any base faa subscription plans
    has_base = [s for s in subscriptions if not s.trial and not s.subscriptionPlan.isAddOn()]
    if has_base:
      # user already has base, so keep only add-ons
      subscription_plans = [p for p in subscription_plans if p.isAddOn()]
    
    # 2nd pass: remove any other plans we already paid for.
    # use key, since our sets of GAE model objects are not ==
    already_owned = [s.subscriptionPlan.key() for s in subscriptions] 
    subscription_plans = [p for p in subscription_plans if p.key() not in already_owned]
        
    template_values = {
      'user': user,
      'user_has_base_subscription': (current_sub is not None and not current_sub.trial),
      'subscriptions': subscriptions,
      'plans': subscription_plans,
      'chargify_sub_domain': CONFIG['chargify_sub_domain'],
      'request': self.request,
      }
    path = os.path.join(os.path.dirname(__file__), 'templates/mySubscriptions.html')
    gns_util.writeTemplate(self, path, template_values)
    


class RefreshUser(webapp.RequestHandler):
  """Handler for /subs/refreshUser."""
  def get(self):
    (user, device) = gns_util.getUserFromRequest(self.request)
    if not user:
      logging.error('No user findable for this request')
      return
    syncUserWithChargify(user)
    self.redirect('/user/show?email=%s' % urllib.quote_plus(user.email))


class ReturnFromChargify(webapp.RequestHandler):
  """Handler for /subs/returnFromChargify.
  
  Do a manual explicit refresh of this user from Chargify, before 
  redirecting to the user's subscriptions page.  This way we make
  sure the latest-greatest info is synced before re-displaying the 
  page.
  """
  @Auth.authenticated
  def get(self):
    user = Auth.AuthenticatedUser(self.request)
    foo = syncUserWithChargify(user)
    self.response.out.write(foo)
    self.redirect('/subs/mySubscriptions')


def syncUserWithChargify(user):
  """Sync the given user with Chargify, updating subscriptions."""
  chargify = Chargify(CONFIG['chargify_api_key'], CONFIG['chargify_sub_domain'])    
  # load the customer from Chargify; our user.key.id is the Chargify reference ID
  c_customer = chargify.Customer().getByReference(user.id())  
  c_subs = c_customer.getSubscriptions()  
  for c_sub in c_subs:
    syncUserChargifySubscription(user, c_sub)


def syncUserChargifySubscription(user, c_sub):
  """Update a user's Subscriptions to match a given Chargify subscription.
  
  This will add or update the Subscription table as necessary.
  """
  # Chargify "product" is our SubscriptionPlan
  plan = models.SubscriptionPlan.gql(
    'WHERE provider = :1 and provider_id = :2', 
    models.SubscriptionProvider.CHARGIFY, c_sub.product.id).get()
  if not plan:
    logging.error('Unable to find SubscriptionPlan with chargify ID %s' % c_sub.id)
    return
      
  subscription = models.Subscription.gql(
    'WHERE user = :1 and subscriptionPlan = :2 and provider_id= :3', user, plan, c_sub.id).get()
  if not subscription:
    # doesn't already exist
    # TODO(mcglincy): do we need to pay attention to the c_subs's dates?
    subscription = gns_util.addSubscriptionPlanToUser(user, plan, None, None)
    # TODO(mcglincy): this is saving twice in a row, which is stupid
    subscription.provider_id = c_sub.id
    subscription.endDate = c_sub.current_period_ends_at      
    subscription.startDate = c_sub.created_at
    subscription.save()
  else:
    if c_sub.state != 'active':
      if c_sub.state == 'canceled':
        subscription.canceled = True
        subscription.endDate = c_sub.current_period_ends_at      
      else:
        subscription.expire()
      
    else:
      subscription.canceled = False
      # TODO(mcglincy): do we want to update any other fields?       
      # current_period_started_at?

      # update our endDate
      # this will effectively "reactivate" an expired subscription
      subscription.endDate = c_sub.current_period_ends_at      
      subscription.startDate = c_sub.created_at
      # make sure we have the backpointer to Chargify
      subscription.provider_id = c_sub.id

    # insert/update it!
  subscription.save()


class ExtendTrial(webapp.RequestHandler):
  def get(self):
    """Find all trial subscriptions with a certain criteria, and extend them."""
    dry_run = False
    fetch_block_size = 100
    end_date = datetime.datetime.strptime('2011-11-07', '%Y-%m-%d')
    subs = models.Subscription.gql('WHERE endDate < :1', end_date).fetch(fetch_block_size)    
    # if we filled up our batch, there are more subscriptions to process
    subs_this_batch = len(subs)
    more_to_process = (subs_this_batch == fetch_block_size)
    
    for sub in subs:
      # only handle trial subscriptions
      if not sub.trial:
        continue
  
      # push back the subscription end date by 30 days
      sub.endDate = sub.endDate + datetime.timedelta(30)

      if not dry_run:
        sub.save()

    # re-request the page to process the next batch, if necessary
    if more_to_process:
      context = {
          'fetch_block_size': fetch_block_size,
          'next_url': '/subs/extendTrial',
      }
      self.response.out.write(template.render('templates/extend_trial.html', context))      
    else:
      self.response.out.write('finished')


class ChargifyWebhook(webapp.RequestHandler):
  def get(self):
    """Handler for /subs/chargifyWebhook."""
    signature = self.request.get('signature')
    if not chargify_util.isChargifyWebhookValid(self.request.body, signature):
      logging.error('Invalid Chargify webhook body')
      return
      
class CancelChargifySubscription(webapp.RequestHandler):
  def get(self):
    subKey = self.request.get('sub')
    #self.response.out.write(subKey)
    subscription = models.Subscription.get(subKey)
    #self.response.out.write(subscription)
    
    chargifySub = ChargifySubscription(CONFIG['chargify_api_key'], CONFIG['chargify_sub_domain'])
    chargifySub = chargifySub.getBySubscriptionId(subscription.provider_id)
    
    
    chargifySub.unsubscribe("instant unsubscribe")
    #chargifySub.delayedUnsubscribe("delayed unsubscribe")
    try: 
      chargifySub.save()
    except:
      None
    #subscription.canceled = True
    #subscription.save()
    
    syncUserWithChargify(subscription.user)
    
    self.redirect('/subs/mySubscriptions')
    
    return
    
class ReactivateChargifySubscription(webapp.RequestHandler):
  def get(self):
    subKey = self.request.get('sub')
    #self.response.out.write(subKey)
    subscription = models.Subscription.get(subKey)
    #self.response.out.write(subscription)

    chargifySub = ChargifySubscription(CONFIG['chargify_api_key'], CONFIG['chargify_sub_domain'])
    chargifySub = chargifySub.getBySubscriptionId(subscription.provider_id)


    chargifySub.reactivate()
    try: 
      chargifySub.save()
    except:
      None
 

    syncUserWithChargify(subscription.user)

    self.redirect('/subs/mySubscriptions')

    return


# ----- mainline ----- #

application = webapp.WSGIApplication([
  ('/subs/webhook', ChargifyWebhook),
  ('/subs/expiredSubscriptions', ExpiredSubscriptions),
  ('/subs/extendTrial', ExtendTrial),
  ('/subs/mySubscriptions', MySubscriptions),
  ('/subs/returnFromChargify', ReturnFromChargify),                                     
  ('/subs/refreshUser', RefreshUser),
  ('/subs/cancelChargify', CancelChargifySubscription),
  ('/subs/reactivate', ReactivateChargifySubscription)
  
  ],
  debug=True)  
                        
def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
