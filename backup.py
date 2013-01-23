from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from boto.ec2.connection import EC2Connection
from google.appengine.api.app_identity import get_application_id

EC2_KEY = 
EC2_SECRET_KEY = 
S3_BUCKET = 
GAE_EMAIL = 
GAE_PASSWORD = 

# The startup script that gets executed on the EC2 instance
STARTUP="""\
#!/bin/bash

cd $HOME

sudo apt-get install -y curl unzip

# Install appengine SDK
# run this twice, the first time it hangs, and it is succesful the second time. Dunno why.
curl -s https://raw.github.com/gist/1012769 | bash &> gaeinstall.out
curl -s https://raw.github.com/gist/1012769 | bash &> gaeinstall2.out

export WORKON_HOME=$HOME/envs
source `which virtualenvwrapper.sh`
workon appengine

pip install boto

# Download/Backup to s3
curl -s http://gaiagpssub.appspot.com/static/backupscript.py > backup.py
# curl -s https://raw.github.com/gist/3783292 > backup.py
python2.7 backup.py --s3bucket '%(s3bucket)s' --app '%(appid)s' --email '%(gae_email)s' --password '%(gae_password)s' --s3_accesskey='%(ec2_key)s' --s3_secretkey='%(ec2_secret_key)s' &> backup.out


shutdown -h now
"""

class BackupHandler(webapp.RequestHandler):
    def get(self):

        # gaiagpssub,gncsub,earthncsub
        appid = get_application_id()
        #appid = 'gaiagpssub,gnssub'
        #appid = "gncsub"

        startup_template = STARTUP % {'appid':appid,
                                          'ec2_key':EC2_KEY,
                                          'ec2_secret_key':EC2_SECRET_KEY,
                                          'gae_email':GAE_EMAIL,
                                          'gae_password':GAE_PASSWORD,
                                          's3bucket':S3_BUCKET
                                          }
                                          
        #self.response.out.write(startup_template)
        conn = EC2Connection(EC2_KEY, EC2_SECRET_KEY,
                validate_certs=False) # AppEngine can't validate certs
        instances = conn.run_instances('ami-057bcf6c',
                            key_name="subBackupsKey",
                            instance_type='m1.small',
                            security_groups=["default"],
                            user_data=startup_template,
                            instance_initiated_shutdown_behavior="terminate",
                            )

        self.response.headers['Content-Type'] = 'text/plain'
        #self.response.write(startup_template)
        self.response.out.write('Started ec2 backup successfully: %s' % instances)
                              

application = webapp.WSGIApplication([('/backup/', BackupHandler)],
        debug=True)  
        
def main():
  #x = FetchMetarData()
  #x.get()
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
                              
