import hashlib
import logging
from xml.dom import minidom
from app_config import CONFIG


def generateHostedURL(page_shortname, resource_id):
  """Generate a full URL for a Chargify hosted page.
  
  E.g., https://gc-test.chargify.com/update_payment/77/13b1ab9996
  """
  token = generateSecretToken(page_shortname, resource_id)
  url = 'https://%s.chargify.com/%s/%s/%s' % (
    CONFIG['chargify_sub_domain'], page_shortname, resource_id, token)
  return url
  
def generateChargifyAPIURL(page_shortname, resource_id):
  """Generate a full URL for a Chargify hosted page.

  E.g., https://gc-test.chargify.com/update_payment/77/13b1ab9996
  """
  url = 'https://%s.chargify.com/%s/%s.json' % (
    CONFIG['chargify_sub_domain'], page_shortname, resource_id)
  return url



def generateSecretToken(page_shortname, resource_id):
  """Generate a secret token for Chargify hosted URLs.
  
  See: http://docs.chargify.com/hosted-page-integration
  """
  s = hashlib.sha1()
  s.update(page_shortname)
  s.update('--')
  s.update(str(resource_id))
  s.update('--')
  s.update(CONFIG['chargify_site_shared_key'])
  # chargify only keeps the first 10 chars
  return s.hexdigest()[0:10]


def isChargifyWebhookValid(post_body, signature):
  m = hashlib.md5()
  m.update(CONFIG['chargify_api_key'])
  m.update(post_body)
  return m.hex_digest() == signature

def errorsFromPayload(payload):
  """Extract errors from chargify payload.
  
  Sample error payload:
    <?xml version="1.0" encoding="UTF-8"?>
    <errors>
      <error>CVV must be 3 or 4 characters long</error>
    </errors>
    
  Returns: list of error strings
  """  
  # clean up incoming XML, removing empty lines and whitespace
  xml = ''.join([l.strip() for l in payload.split('\n')])
  
  errors = []
  try:
    dom = minidom.parseString(xml)
    if dom.documentElement.tagName == 'errors':
      errors = [n.lastChild.wholeText for n in dom.documentElement.childNodes]
  except Exception, e:
    # couldn't parse
    logging.error('%s - could not parse chargify payload %s' % (e, payload))
  return errors
  
