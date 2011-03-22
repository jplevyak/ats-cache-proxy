#!/usr/bin/env python
""" update_config.py

Checks a config file server for updated versions of any configuration files,
and if an updated version of a file is found, downloads it.

The original config file is backed up (although only the most recent version
is kept and successive backups will overwrite any backups that were already in
there).

Configuration is kept in config.py
"""
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib

import config

def check_remote_version(filename):
    """ Checks to see if an update is required by comparing the local/remote
    versions of a file. """
    logging.info("Checking if an update is required for %s" % filename)
    try:
        fh = urllib.urlopen('http://%s/check?name=%s' % (
            config.conf_server, filename))
        remote_version = fh.read()
    except IOError, e:
        logging.error("Server Error: %s" % e.strerror)
        return -1
    try:
        remote_version = int(remote_version)
    except ValueError:
        logging.error("Unable to determine remote version for: %s" % filename)
        return -1
    return remote_version

def get_local_version_info():
    """Opens and parses the version information file"""
    logging.debug("Retrieving local version information from: %s" %
                  config.version_file)
    versions = {}
    try:
        fh = open(config.version_file)
    except IOError, e:
        # Return empty if the file doesn't exist
        if e.errno == 2: # File not found
            return {}
        else:
            raise
    for line in fh:
        if not line or line[0] == '#':
            # Skip blank lines and # comments
            continue
        try:
            filename, version = [part.strip() for part in line.split('=')]
            version = int(version)
        except ValueError:
            pass # Skip malformed lines
        versions[filename] = version
    fh.close()
    return versions

def save_local_version_info(versions):
    """Store the local version file"""
    logging.debug("Saving local version information to: %s" %
                  config.version_file)
    fh = open(config.version_file, "w")
    fh.write("# Configuration file updater version file - do not edit\n")
    for filename, version in versions.items():
        fh.write("%s = %s\n" % (filename, version))
    fh.close()

def fetch_new_config_file(name, local_filename):
    """Backs up the existing file and fetches an updated one from the
    server"""
    logging.info("Fetching new config file: %s" % name)
    logging.debug("Backup up original config file to %s/%s" % 
                  (config.backup_dir, name))
    try:
        os.makedirs(config.backup_dir)
    except OSError:
        pass
    try:
        shutil.copy(local_filename, "%s/%s" % (config.backup_dir, name))
    except IOError, e:
        logging.warning("Backup of original file failed: %s" % e)
    logging.debug("Retrieving config file from: %s to %s" %
                  (config.conf_server, local_filename))

    try:
        (tempfile, headers) = urllib.urlretrieve("http://%s/fetch?name=%s" %
                                                (config.conf_server, name))
        try:
            shutil.copymode(local_filename, tempfile)
        except IOError:
            pass
        shutil.move(tempfile, local_filename)
    except (IOError, OSError), e:
        logging.error("Unable to retrieve updated config file: %s" %
                      e.strerror)
        return False
    return True

def run_script(cmdtype, name):
    try:
        cmd = config.scripts[name][cmdtype]
    except KeyError:
        return
    logging.debug("Running %s script for %s: %s" % (cmdtype, name, cmd))
    retcode = subprocess.call(cmd, shell=True)
    if retcode != 0:
        logging.warning("Command failed with exit code %d: %s" %
                        (retcode, cmd))

def write_last_updated_time(filename):
    fh = open(filename, "w")
    fh.write(time.strftime("%c") + "\n")
    fh.close()

if __name__ == '__main__':
    logging.basicConfig(
        level=config.loglevel,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    if not config.auto_update:
        logging.debug("Auto update disabled. Exiting")
        sys.exit(0)
    versions = get_local_version_info()
    for name, local_filename in config.files.items():
        remote_version = check_remote_version(name)
        local_version = versions.setdefault(name, -1)
        logging.debug("Remote version: %s, Local Version: %s" %
                      (remote_version, local_version))
        if remote_version > local_version:
            run_script('pre', name)
            if fetch_new_config_file(name, local_filename):
                versions[name] = remote_version
            run_script('post', name)
    save_local_version_info(versions)
    write_last_updated_time(config.last_updated_file)
