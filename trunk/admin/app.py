#!/usr/bin/env python
import bottle
import functools
import json
import re
import subprocess
import time
import urllib2
import uuid

default_config_path="/www/admin/etc/defaultconfig.json"
config_file_path="/www/etc/config.json"
last_updated_path="/www/etc/last_updated"
auto_update_path="/www/bin/update_config.py"
config = {}

def password_protected_page(f):
    @functools.wraps(f)
    def new_f(*args, **kwargs):
        auth = bottle.request.auth
        if auth:
            if auth[0] == 'admin' and auth[1] == 'foobar':
                f(*args, **kwargs)
                return
        bottle.response.headers['WWW-Authenticate'] = \
            'Basic realm="Console"'
        bottle.abort(401, "Authorization required")
    return new_f

@password_protected_page
@bottle.route("/")
def index():
    return bottle.template("index", proxy_state=current_proxy_state(),
                          config=config, last_updated=last_updated())

@password_protected_page
@bottle.route("/static/:filename")
def static(filename):
    return bottle.static_file(filename, root='static')

@bottle.route("/favicon.ico")
def favicon():
    return static("favicon.ico")

def get_client_id():
    """ Generates a UUID to be used as the client ID, and stores it for future
    use, fetching the stored version when repeatedly called.
    """
    clientid_cache='/var/tmp/.squidstats_clientid'
    client_id = ""
    # First try to see if we have a cached ID
    try:
        fh = open(clientid_cache)
        client_id = fh.readline()
        fh.close()
    except IOError:
        pass

    # Make sure the cached ID looks like a valid UUID
    try:
        if client_id == str(uuid.UUID(client_id)):
            return client_id
    except ValueError:
        # The client ID didn't look like a valid UUID, let's make a new one
        pass
    # Client id was invalid
    return None

@password_protected_page
@bottle.get("/view_stats")
def view_stats():
    client_id = get_client_id()
    if not client_id:
        return "Client ID unknown. Unable to fetch stats"
    fh = urllib2.urlopen('http://%s/getstats?client_id=%s' % (
        config['stats_server'], client_id))
    try:
        stats = json.load(fh)
    except ValueError:
        return "Unable to fetch stats from server"
    fh.close()
    if not stats:
        return "No statistics are available for this client"
    params = {
        'cache_size_total': 0,
        'hit_rate_total': 0,
        'hit_rate_latest': stats[-1]['hit_rate'],
        'cache_size_latest': stats[-1]['cache_size'],
        'date_from': time.strftime("%c", time.localtime(stats[0]['date'])),
        'date_to': time.strftime("%c", time.localtime(stats[-1]['date']))
    }
    for s in stats:
        params['cache_size_total'] += s['cache_size']
        params['hit_rate_total'] += s['hit_rate']
    params['cache_size_avg'] = params['cache_size_total']/len(stats)
    params['hit_rate_avg'] = params['hit_rate_total']/len(stats)
    return bottle.template("stats", **params)

@password_protected_page
@bottle.post("/proxy_status")
def proxy_status_update():
    action = bottle.request.forms.get('action')
    response = {"status": "BAD",
                "message": "Unknown action",
                "state": "unknown"}
    if action == "stop":
        response['status'] = "OK"
        response['message'] = "Stopping proxy server"
        service("trafficserver", "stop")
    if action == "start":
        response['status'] = "OK"
        response['message'] = "Starting proxy server"
        service("trafficserver", "start")
    response['state'] = current_proxy_state()
    return json.dumps(response)

@password_protected_page
@bottle.post("/config_update")
def config_update():
    response = {"status": "BAD",
                "message": "Failed to update config item"}
    key = bottle.request.forms.get('key')
    value = bottle.request.forms.get('value')
    # Hack for boolean values
    if value == "true":
        value = True
    elif value == "false":
        value = False
    # Only update existing values
    if config.has_key(key):
        config[key] = value
        save_config()
        response['status'] = "OK"
        if type(value) is bool:
            response['message'] = "%s has been %s" % (
                key, "enabled" if value else "disabled")
        else:
            response['message'] = "%s changed to %s" % (key, value)
    return json.dumps(response)

def current_proxy_state():
    output = subprocess.Popen(["service", "trafficserver", "status"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
    try:
        status = output.split()[1]
    except IndexError:
        return "unknown"
    if status.find("stop/waiting") != -1:
        return "stopped"
    if status.find("stop/") != -1:
        return "stopping"
    if status.find("start/running") != -1:
        return "started"
    if status.find("start/") != -1:
        return "starting"
    return "unknown"

def service(service, command):
    return subprocess.Popen(["service", service, command],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

@password_protected_page
@bottle.route("/update_now")
def run_auto_update():
    response = {
        'status' : "BAD",
        'message' : "Failed to run update command",
        'output': ''
    }
    try:
        p = subprocess.Popen([auto_update_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outtuple = p.communicate()
        output = outtuple[0] + outtuple[1] # Combine stdout/stderr
        retcode = p.returncode
        if retcode == 0:
            response['status'] = "OK"
            response['message'] = "Update complete"
        else:
            response['message'] = "Update failed"
        response['output'] = output
    except OSError:
        pass
    return response

@password_protected_page
@bottle.route('/last_update')
def last_update_page():
    return json.dumps({'last_update': last_updated()})

def last_updated():
    try:
        fh = open(last_updated_path)
    except IOError:
        return "unknown"
    line = fh.readline()
    fh.close()
    return line

def load_config(filename):
    try:
        fh = open(filename)
    except IOError:
        return
    config.update(json.load(fh))
    fh.close()

def save_config():
    with open(config_file_path, "w") as fh:
        json.dump(config, fh)

# Load config file, but load defaults first (they'll be overridden by anything
# in the real config)
load_config(default_config_path)
load_config(config_file_path)

#bottle.debug(True)
#bottle.run(host="0.0.0.0", port="8081")
bottle.run(host="0.0.0.0", port="80")
