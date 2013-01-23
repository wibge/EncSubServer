# base shared configuration dict
BASE = dict(
  appname = 'GAIA',
  display_name = "Gaia GPS",
  default_appcode = 'gaia',
  default_dataset = 'gaiagreen',
  name='base',
  
  iapp_password='ed973271200d45fd9c31538d66c6ac68',
  free_trial_identifier = '1MONTHTRIAL',
  base_template = "gaia/gaia_base.html",
  base_css = "gaia.css",
  
  
  #TODO replace with good email addresses
  email_address = "Gaia GPS Subscriptions <wibge@gmail.com>",
  password_reset_email_address = "Gaia GPS Password Reset <wibge@gmail.com>"
)

# overrides for test environment
TEST = dict(
  name='test',
  host='gaiagpssub.beta.appspot.com',
  #chargify_api_key = 'Uqh6IR26enxznjvzUBKi',
  #chargify_sub_domain = 'globalnavsource-test',
  #chargify_site_shared_key = 'wS4u3eshisxUs484CvGi',
)

# overrides for live environment
LIVE = dict(
  name='live',
  host='gaiagpssub.appspot.com',
  #chargify_api_key = 'Uqh6IR26enxznjvzUBKi',
  #chargify_sub_domain = 'globalnavsource',
  #chargify_site_shared_key = 'kTGPY5Rxbnnui2I-M3VZ',
)
