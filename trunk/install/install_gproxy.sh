#!/bin/bash
#
# Install the traficserver based proxy server from scratch.
#
###############################################################################
# Configuration
###############################################################################
UNAME=`uname -m`
if [[ $UNAME == "x86_64" ]]; then
    TS_DEB="trafficserver_2.1.4-unstable-1_amd64.deb"
else
    TS_DEB="trafficserver_2.1.4-unstable-1_i386.deb"
fi
TSPREFIX=/opt/ts
TSPLUGINDIR=$TSPREFIX/libexec
TSCONFDIR=$TSPREFIX/etc
PROXYPORT=8080
CACHESIZE="3G" # Disk cache size

LOGFILE=$PWD/install.log
COLOR=
[[ -t 1 ]] && COLOR=1 # Turn on color if stdout is a terminal

###############################################################################
# Log/message functions
###############################################################################
setup_color() {
    if [[ -n $COLOR ]]; then
        B=`tput bold``tput setaf 2` # Bullet point - green
        E=`tput bold``tput setaf 1` # Error - red
        H=`tput bold``tput setaf 6` # Highlight - cyan
        N=`tput sgr0`    # Reset - normal
    else
        B=
        E=
        H=
        N=
    fi
}

log() {
    echo " $B*$N $@"
    echo " * $@" >> $LOGFILE
}

error() {
    echo " $B*$N ${E}ERROR:$N $@"
    echo " * ERROR: $@" >> $LOGFILE
    exit 1
}

require_root() {
    [[ $UID == 0 ]] || {
        error "This script must be run as root"
    }
}

logcmd() {
    # Run a command, but redirect all output to the logfile
    echo " * Running command: $@" >> $LOGFILE
    "$@" >> $LOGFILE 2>&1 || \
        error "Failed to run $@"
}

###############################################################################
# Main script
###############################################################################
setup_color
require_root

# This assumes trafficserver is pre-built and is available as a .deb package
# If building from source, version 2.1.4 is needed with the following two
# patches applied:
# https://issues.apache.org/jira/secure/attachment/12459300/ts-526-patch.txt
# https://issues.apache.org/jira/secure/attachment/12459301/ts-527-patch.txt
log "Installing trafficserver package"
logcmd dpkg -i $TS_DEB

# This should be done in the package, but we fix a few thing here for now
log "Fixing permissions"
logcmd chown nobody $TSPREFIX/var/trafficserver
logcmd chown nobody $TSPREFIX/var/log/trafficserver
logcmd chown nobody $TSCONFDIR
logcmd chown nobody $TSCONFDIR/*

log "Setting up trafficserver configuration"
logcmd cp cacheurl.config $TSPLUGINDIR
logcmd sed -i \
    -e 's/\(proxy.config.url_remap.remap_required INT\) 1/\1 0/' \
    -e "s/\\(proxy.config.http.server_port INT\\) [0-9]\+/\\1 $PROXYPORT/" \
    -e 's/\(proxy.config.http.background_fill_active_timeout INT\) [0-9]\+/\1 3600/' \
    -e 's/\(proxy.config.http.background_fill_completed_threshold FLOAT\) [0-9.]\+/\1 0.05/' \
    -e 's/\(proxy.config.http.server_port_attr STRING\) X/\1 >/' \
    $TSCONFDIR/records.config
logcmd sed -i "s/\\(var\/trafficserver\\) 256MB/\\1 $CACHESIZE/" \
    $TSCONFDIR/storage.config
# These aren't logged because they're just echo commands
# should probably find a way to fix this
echo "cacheurl.so" >> $TSCONFDIR/plugin.config
cat >> $TSCONFDIR/cache.config <<EOT
# Force cache youtube videos
url_regex=http:\/\/(.*\.youtube\.com|.*\.googlevideo\.com|.*\.video\.google\.com)\/(get_video|videoplayback|videodownload)\?.*?\&itag=[0-9]*.*?\&id=[a-zA-Z0-9]* ttl-in-cache=5d
# Keyhole (google earth)/maps servers
url_regex=(kh|mt)[0-9]*\.google\.com.*?\/.*? ttl-in-cache=5d
EOT

log "Compiling cacheurl plugin"
pushd ../trafficserver_cacheurl > /dev/null
logcmd make
logcmd cp cacheurl.so $TSPLUGINDIR
popd > /dev/null

log "Setting up trafficserver init (upstart) script"
logcmd cp trafficserver.conf /etc/init/
logcmd ln -sf /lib/init/upstart-job /etc/init.d/trafficserver

log "Installing admin interface"
logcmd mkdir -p /www
logcmd cp -R ../admin /www/admin
logcmd mkdir -p /www/etc
logcmd cp /www/admin/etc/defaultconfig.json /www/etc/config.json

log "Installing update/stats scripts"
logcmd mkdir -p /www/bin
logcmd cp ../client_scripts/* /www/bin/
# Overwrite the sample config with the 'real' config for updating
logcmd mv /www/bin/liveconfig.py /www/bin/config.py

log "Installing cron jobs"
logcmd cp crontab /etc/cron.d/gproxy

log "Setting up admin console init (upstart) script"
logcmd cp adminconsole.conf /etc/init/
logcmd ln -sf /lib/init/upstart-job /etc/init.d/adminconsole

log "Starting services"
logcmd service trafficserver start
logcmd service adminconsole start
