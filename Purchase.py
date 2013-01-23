import Auth
import chargify_util
import datetime
import gns_util
import logging
import models
import os

from app_config import CONFIG
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from pychargify.api import *

class PurchaseForm(webapp.RequestHandler):
  @Auth.authenticated
  def get(self):
    """Display the purchase form."""
    user = Auth.AuthenticatedUser(self.request)
    identifier = self.request.get('plan_identifier')
    plan = models.SubscriptionPlan.gql(
      'WHERE identifier = :1', identifier).get()
      
    # look up the product and pricing from chargify
    chargify = Chargify(CONFIG['chargify_api_key'], CONFIG['chargify_sub_domain'])
    logging.error('LOG')
    logging.error(plan.provider_id)
    logging.error('LOG')
    product = chargify.Product().getById(plan.provider_id)

    template_values = {
      'request': self.request,
      'user': user,
      'plan': plan,
      'price': product.getFormattedPrice(),
      }
    path = os.path.join(os.path.dirname(__file__), 'templates/purchaseForm.html')
    gns_util.writeTemplate(self, path, template_values)
    
  @Auth.authenticated
  def post(self):
    """Process the purchase form."""
    user = Auth.AuthenticatedUser(self.request)
    
    # TODO: validate form fields
    cc_number = self.request.get('cc_number')
    cc_cvv = self.request.get('cc_cvv')
    cc_exp_month = self.request.get('cc_exp_month')
    cc_exp_year = self.request.get('cc_exp_year')
    first_name = self.request.get('first_name')
    last_name = self.request.get('last_name')
    billing_address = self.request.get('billing_address')
    billing_city = self.request.get('billing_city')
    billing_state = self.request.get('billing_state')
    billing_zip = self.request.get('billing_zip')   
    billing_country = self.request.get('billing_country')
    coupon_code = self.request.get('coupon_code')
 
    identifier = self.request.get('plan_identifier')
    plan = models.SubscriptionPlan.gql(
      'WHERE identifier = :1', identifier).get()
      
    chargify = Chargify(CONFIG['chargify_api_key'], CONFIG['chargify_sub_domain'])    

    creditcard = chargify.CreditCard('credit_card_attributes')
    creditcard.full_number = cc_number
    creditcard.cvv = cc_cvv
    creditcard.expiration_month = cc_exp_month
    creditcard.expiration_year = cc_exp_year
    creditcard.billing_address = billing_address
    creditcard.billing_city = billing_city
    creditcard.billing_state = billing_state
    creditcard.billing_zip = billing_zip
    creditcard.billing_country = billing_country

    subscription = chargify.Subscription()
    subscription.product_id = plan.provider_id
    subscription.credit_card = creditcard
    subscription.coupon_code = coupon_code
    
    # first check if this user already has a Chargify Customer record
    customer = None
    try:
      # customer exists, so only set subscription customer_id
      # this ends up creating XML request data as:
      # <subscription>
      #  <customer_id>123</customer_id>
      #  ...
      customer = chargify.Customer().getByReference(user.id())
      subscription.customer_id = customer.id
    except ChargifyNotFound:
      # not found, so create a new customer, via the
      # customer_attributes tag.  I.e.,
      # <subscription>
      #   <customer_attributes>
      #     ...
      customer = chargify.Customer('customer_attributes')
      customer.first_name = first_name
      customer.last_name = last_name
      customer.email = user.email
      customer.reference = user.id()
      subscription.customer = customer
    
    # save the new subscription to chargify    
    try:
      subscription.save()
      self.redirect('/subs/returnFromChargify')
    except ChargifyError, ce:
      errors = []
      if ce.args:
        # try to extract chargify error strings from the payload
        payload = ce.args[0]
        errors = chargify_util.errorsFromPayload(payload)
        logging.error(errors)

      product = chargify.Product().getById(plan.provider_id)        
      template_values = {
        'request': self.request,
        'user': user,
        'plan': plan,
        'price': product.getFormattedPrice(),
        'errors': errors,
        #
        'cc_number': cc_number,
        'cc_cvv': cc_cvv,
        'cc_exp_month': cc_exp_month,
        'cc_exp_year': cc_exp_year,
        'first_name': first_name,
        'last_name': last_name,
        'billing_address': billing_address,
        'billing_city': billing_city,
        'billing_state': billing_state,
        'billing_zip': billing_zip,
        'billing_country': billing_country,
        'coupon_code': coupon_code,
      }
      path = os.path.join(os.path.dirname(__file__), 'templates/purchaseForm.html')
      gns_util.writeTemplate(self, path, template_values)


application = webapp.WSGIApplication([
  ('/purchase/form', PurchaseForm),
  ],
  debug=True)  
                        
def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
  
