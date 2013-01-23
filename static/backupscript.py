
#!/usr/bin/env python

# Prereqs:
#
#   * appcfg.py (appengine) -- https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python
#   * boto
#
# Usage:
#
#   python backup.py --s3bucket <bucketname> --app <appid> --email=<google_email> --password=<google_password> --s3_accesskey=<s3_accesskey> --s3_secretkey=<s3_secretkey>
#
import argparse
import datetime
import fcntl
import logging
import os
import shutil
import subprocess

from datetime import timedelta
from boto.s3.connection import S3Connection
from boto.s3.key import Key


FORMAT = '%(asctime)s %(levelname)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("boto").setLevel(logging.INFO)
_log = logging.getLogger('appengine.backup')

MONTH_DAYS = 30  # *shrug*
DEBUG=False

script_start_time = datetime.datetime.now()+timedelta(days=9)

_touch = lambda fname: os.utime(fname, None) if os.path.exists(fname) else open(fname, "w").close()
_get_backup_filename = lambda: "backup_"+script_start_time.strftime("%Y%m%d")+".sqlite"
_get_backup_dir      = lambda app, type: os.path.join("backups", app, type) + "/"
_get_backup_path     = lambda app, type: os.path.join("backups", app, type, _get_backup_filename())


### Main commands


def download_file(app, email, password):

    filename = "%s.backup.sqlite.tmp" % app
    _log.info("Downloading backup for app '%s' to '%s'" % (app, filename))

    if os.path.exists(filename):
        _log.warning("File already exists.  Skipping download")
        return filename

    if DEBUG:
        _touch(filename)
    else:
        pwd = subprocess.Popen(["echo", password], stdout=subprocess.PIPE)
        proc = subprocess.Popen(["appcfg.py",
                #"--noauth_local_webserver",
                #"--oauth2_refresh_token=%s" % refresh_token,
                "download_data",
                "--url=http://%s.appspot.com/_ah/remote_api" % app,
                "--filename=%s" % filename,
                "--email=%s" % email,
                "--passin",
                "--log_file=%s.log" % app,
                "--db_filename=%s_progress.sql3" % app,
                "--result_db_filename=%s_results.sql3" % app,
                "--rps_limit=30000",
                "--bandwidth_limit=100000000",
                "--batch_size=500",
                "--http_limit=32",
                "--num_threads=30",
        ], stdout=subprocess.PIPE, stdin=pwd.stdout)
        pwd.stdout.close()
        stdout_text, stderr_text = proc.communicate()
        pwd.wait()
    return filename

class S3Sync(object):

    def __init__(self, appid, s3bucket):
        self.appid = appid
        self.s3bucket = s3bucket

    def put_backup_in_s3(self, type, filename):
        """Puts a backup file into s3"""
        k = Key(self.s3bucket)
        k.key = _get_backup_path(self.appid, type)
        _log.info("Putting %s into s3" % k.key)
        k.set_metadata("backup_date", script_start_time.strftime("%s"))
        k.set_contents_from_filename(filename)

    def copy_backup(self, from_type, to_type):
        """Copies a backup from one location to another.  Useful so you don't need
            to upload a file multiple times"""
        from_path = _get_backup_path(self.appid, from_type)
        to_path = _get_backup_path(self.appid, to_type)
        _log.info("Copying backup file from %s to %s" % (from_path, to_path))
        self.s3bucket.copy_key(
                new_key_name=to_path,
                src_bucket_name=self.s3bucket.name,
                src_key_name=from_path,
                preserve_acl=True,
                )

    def has_backup_in_time(self, type, delta):
        """Returns whether a backup of "type" exists since the delta"""
        app = self.appid
        backup_dir = _get_backup_dir(app, type)
        _log.debug("Getting backup list for %s" % backup_dir)
        filelist = self.s3bucket.list(prefix=backup_dir, delimiter="/")
        filelist = [self.s3bucket.get_key(i.key) for i in filelist]

        try:
            newest = max([int(x.get_metadata("backup_date")) for x in filelist])
            newest = datetime.datetime.fromtimestamp(newest)
        except ValueError: # List was empty
            _log.debug("No files in s3 -- so no newest file")
            return False
        _log.debug("Newest in s3 has date %s" % newest.isoformat())
        return newest > script_start_time - delta

    def prune_old_files(self, type, delta):
        """Prunes files older than the delta"""
        app = self.appid
        _log.info("Pruning old files for app %s of type %s" % (app, type))

        backup_dir = _get_backup_dir(app, type)
        filelist = self.s3bucket.list(prefix=backup_dir, delimiter="/")
        filelist = [self.s3bucket.get_key(i.key) for i in filelist]

        cutoff = script_start_time - delta
        for key in filelist:
            backup_date = datetime.datetime.fromtimestamp( int(key.get_metadata("backup_date")) )
            if backup_date < cutoff:
                _log.debug("Pruning s3 object %s with date %s" % (key.key, backup_date.isoformat()))
                self.s3bucket.delete_key(key.key)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--email', help="The Google accounts email address to use.", required=True)
    parser.add_argument('--password', help="The Google accounts password to use.", required=True)
    parser.add_argument('--app', help="An app-name to backup", required=True, dest="apps", type=lambda v: v.split(","))
    parser.add_argument('--s3bucket', help="The s3bucket to upload to", required=True)
    parser.add_argument('--s3_accesskey', help="The s3 access key to use", required=True)
    parser.add_argument('--s3_secretkey', help="The s3 secret key to use", required=True)

    args = parser.parse_args()

    conn = S3Connection(args.s3_accesskey, args.s3_secretkey)
    bucket = conn.create_bucket(args.s3bucket)
    bucket.set_acl("private")

    # Temporary for testing
    bucket.delete_keys(["backups/gnssub/daily/backup_20120930.sqlite", "backups/gnssub/weekly/backup_20120930.sqlite", "backups/gnssub/monthly/backup_20120930.sqlite"])

    # Download them all serially for now

    for app in args.apps:
        filename = download_file(app, args.email, args.password)

        s3sync = S3Sync(app, bucket)
        s3sync.put_backup_in_s3("daily", filename)

        os.unlink(filename)

        if not s3sync.has_backup_in_time("weekly", timedelta(days=7)):
            s3sync.copy_backup("daily", "weekly")

        if not s3sync.has_backup_in_time("monthly", timedelta(days=MONTH_DAYS)):
            s3sync.copy_backup("daily", "monthly")

        s3sync.prune_old_files("daily", timedelta(days=7))
        s3sync.prune_old_files("weekly", timedelta(days=MONTH_DAYS))
        s3sync.prune_old_files("monthly", timedelta(days=MONTH_DAYS*4))
