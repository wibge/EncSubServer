from google.appengine.api import app_identity

# base shared configuration dict
BASE = dict(
  appname = 'EFB',
  display_name = "EFB",
  default_appcode = 'efb',
  default_dataset = 'faa',
  name='base',
  iapp_password='b07c6dc0182c4be4b468816dee06db18',
  free_trial_identifier = '2MONTHTRIAL',
  email_address = "EFB Dataplans <dataplans@globalnavsource.com>",
  password_reset_email_address = "EFB Password Reset <dataplans@globalnavsource.com>",
  base_template = "gns/gns_base.html",
  base_css = "gns.css"
)

# overrides for test environment
TEST = dict(
  name='test',
  host='gnsbeta.appspot.com',
  chargify_api_key = 'Uqh6IR26enxznjvzUBKi',
  chargify_sub_domain = 'globalnavsource-test',
  chargify_site_shared_key = 'wS4u3eshisxUs484CvGi',
)

# overrides for live environment
LIVE = dict(
  name='live',
  host='gnssub.appspot.com',
  chargify_api_key = 'Uqh6IR26enxznjvzUBKi',
  chargify_sub_domain = 'globalnavsource',
  chargify_site_shared_key = 'kTGPY5Rxbnnui2I-M3VZ',
)

# configure the global CONFIG instance based on app engine app ID
LIVE_APP_ID = 'gnssub'
CONFIG = None

if app_identity.get_application_id() == 'earthncsub':
  LIVE_APP_ID = 'earthncsub'
  from enc_app_config import *
  
if app_identity.get_application_id() == 'gaiagpssub':
  LIVE_APP_ID = 'gaiagpssub'
  from gaia_app_config import *

class Config(object):
  """Simple configuration holder to support base and override configuration dicts.
  
  Properties can be accessed via standard dictionary [] and get().
  """
  def __init__(self, base_config=BASE, override_config=TEST):
    self.base_config = base_config
    self.override_config = override_config
      
  def __getitem__(self, key):
    return self.override_config.get(key, self.base_config.get(key))
    
  def get(self, key, default=None):
    val = self.__getitem__(key)
    if val:
      return val
    return default



# for details on app identity, 
# see http://code.google.com/appengine/docs/python/appidentity/overview.html
if app_identity.get_application_id() == LIVE_APP_ID:
  CONFIG = Config(base_config=BASE, override_config=LIVE)
else:
  CONFIG = Config(base_config=BASE, override_config=TEST)

