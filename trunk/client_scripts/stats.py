#!/usr/bin/env python
""" stats.py

Fetches cache statistics from squid and uploads them to google app engine.

Prints a message to stdout on failure, otherwise nothing is printed.

Stats are associated with a client ID, which is generated on the first run
using the uuid module (uuid1 - mac address based) and stored in a file for
successive runs.
"""
import socket
import re
import uuid
import urllib
import urllib2
import json
import sys
import subprocess

config_file = '/www/etc/config.json'
traffic_line = '/opt/ts/bin/traffic_line'
with open(config_file) as fh:
    config = json.load(fh)

#debug = True
debug = False

def get_squid_stats():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 3128))
    s.send("GET cache_object://localhost/info HTTP/1.0\n\n")
    fh = s.makefile()
    stats = {}
    for line in fh:
        match = re.search("Storage Swap size:\t(\d+) KB", line)
        if match:
            stats['cache_size'] = match.group(1)
        match = re.search("Request Hit Ratios:\t5min: ([0-9.]+)%", line)
        if match:
            stats['hit_rate'] = match.group(1)
    fh.close()
    s.close()
    return stats

def get_ats_stat(stat_name):
    output = subprocess.Popen([traffic_line, "-r", stat_name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
    return output

def get_ats_stats():
    stats = {}
    stats['hit_rate'] = int(float(get_ats_stat('proxy.node.cache_hit_ratio'))
        * 100)
    stats['cache_size'] = int(get_ats_stat('proxy.process.cache.bytes_used'))
    return stats


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

    # If not, then generate one
    client_id = str(uuid.uuid1())
    fh = open(clientid_cache, "w")
    fh.write(client_id)
    return client_id

def post_stats(stats, server):
    data = stats.copy()
    data['client_id'] = get_client_id()
    try:
        fh = urllib2.urlopen("http://%s/sendstats" % server,
            urllib.urlencode(data))
    except urllib2.URLError, e:
        print "Failed to upload stats:", e

    for line in fh:
        if re.search("^OK", line):
            return
        if re.search("^FAILED:", line):
            print line

if __name__ == '__main__':
    if not config['upload_stats']:
        if debug:
            print "Stats sending is disabled. Exiting."
        sys.exit(0)
    stats = get_ats_stats()
    if debug:
        print stats
    post_stats(stats, config['stats_server'])
