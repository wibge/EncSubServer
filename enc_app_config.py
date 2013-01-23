# base shared configuration dict
BASE = dict(
  appname = 'ENC',
  display_name = "EarthNC",
  default_appcode = 'enc',
  default_dataset = 'encblue',
  name='base',
  
  iapp_password='605a71eb77ba42d299ca0b19585f444f',
  free_trial_identifier = '1MONTHTRIAL',
  base_template = "earthnc/enc_base.html",
  base_css = "enc.css",
  
  
  #TODO replace with ENC email addresses
  email_address = "ENC Dataplans <wibge@gmail.com>",
  password_reset_email_address = "ENC Password Reset <wibge@gmail.com>"
)

# overrides for test environment
TEST = dict(
  name='test',
  host='earthncsub.beta.appspot.com',
  #chargify_api_key = 'Uqh6IR26enxznjvzUBKi',
  #chargify_sub_domain = 'globalnavsource-test',
  #chargify_site_shared_key = 'wS4u3eshisxUs484CvGi',
)

# overrides for live environment
LIVE = dict(
  name='live',
  host='earthncsub.appspot.com',
  #chargify_api_key = 'Uqh6IR26enxznjvzUBKi',
  #chargify_sub_domain = 'globalnavsource',
  #chargify_site_shared_key = 'kTGPY5Rxbnnui2I-M3VZ',
)
