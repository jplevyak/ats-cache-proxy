import logging
import json

# Fetch the admin console config
admin_config_file = "/www/etc/config.json"
try:
    fh = open(admin_config_file)
    admin_config = json.load(fh)
except IOError:
    admin_config = {}

# List of files to retrieve
# The key is the filename on the server, the value is the full path to
# configuration file locally
files = {
    # Currently, nothing is set to fetch automatically. Add files here
    #'squid-google.conf' : '/www/etc/squid-google.conf'
}

# Pre/post scripts - does not have to be present for every file, and if
# desired, only one of pre/post have to be specified.
# Format:
#   'filename' : {
#       'pre' : '/path/to/script',
#       'post': '/path/to/script'
#   }
scripts = {
    'squid-google.conf': {
        'post': '/usr/sbin/squid -f /www/etc/squid.conf -k reconfigure'
    }
}

loglevel=logging.DEBUG

# Filename to use to store version metadata
version_file = '/var/tmp/.conffile_versions'

# Server to retrieve configuration from
conf_server = admin_config.get('update_server')

# Enable/disable automatic updating
auto_update = admin_config.get('auto_update')

# Store last updated time here
last_updated_file = '/www/etc/last_updated'

# Directory to back up replaced files to
backup_dir = '/var/tmp/config_file_backups'
