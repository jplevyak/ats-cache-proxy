import cgi
import os
import uuid
import time
import datetime

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

# Google app engine has simplejson instead of the built in json
from django.utils import simplejson as json

import wsgiref.handlers

class ConfigFile(db.Model):
    """A configuration file"""
    name = db.StringProperty()
    content = db.TextProperty()
    uploaded_date = db.DateTimeProperty(auto_now_add=True)
    version = db.IntegerProperty()

    @classmethod
    def get_latest_version(classname, name):
        return ConfigFile.gql("""WHERE name = :name
                           ORDER BY version DESC
                           LIMIT 1""", name=name)[0]

class CacheStats(db.Model):
    """An entry for cache statistics"""
    client_id = db.StringProperty()     # Supplied by client - uuid
    cache_size = db.IntegerProperty()   # In KB
    hit_rate = db.FloatProperty()       # Percentage
    date = db.DateTimeProperty(auto_now_add=True)

class BaseRequestHandler(webapp.RequestHandler):
    """Base request handler with some helper functions"""
    def errormsg(self, message):
            self.template_render("error", { 'message': message })

    def message(self, message):
            self.template_render("message", { 'message': message })

    def template_render(self, template_file, template_values={}):
        path = os.path.join(os.path.dirname(__file__), 'templates',
                            "%s.html" % template_file)
        self.response.out.write(template.render(path, template_values))

class IndexPage(BaseRequestHandler):
    def get(self):
        self.template_render("index")

class FetchConfigFile(BaseRequestHandler):
    def get(self):
        name = self.request.get('name')
        version = self.request.get('version')
        if version:
            try:
                version = int(version)
            except ValueError:
                self.errormsg("Version must be numeric")
                return
        if name == '':
            self.errormsg("Name is required")
        else:
            if version:
                try:
                    config_file = ConfigFile.gql("""WHERE name = :name
                                                 AND version = :version""",
                                                 name=name,
                                                 version=version)[0]
                except IndexError:
                    self.errormsg("Config file %s version %s not found" %
                              (name, version))
                    return
            else:
                try:
                    config_file = ConfigFile.get_latest_version(name)
                except IndexError:
                    self.errormsg("Config file %s not found" % name)
                    return
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write(config_file.content)

class StoreConfigFile(BaseRequestHandler):
    def get(self):
        self.template_render("store")

    def post(self):
        name = cgi.escape(self.request.get('name'))
        content = self.request.params.get('content', None)
        if not isinstance(content, cgi.FieldStorage):
            self.errormsg("No file was uploaded")
            return
        if name == '':
            name = content.filename
        content = content.file.read()
        try:
            latest = ConfigFile.get_latest_version(name)
            last_version = latest.version
        except IndexError, e:
            last_version = 0
        version = last_version + 1
        config_file = ConfigFile(name=name, content=content,
                                 version=version)
        config_file.put()
        self.message("""Stored new config file:
                     <a href=\"/fetch?name=%s\">%s</a> version %s""" % (
                         name, name, version))

class ListFiles(BaseRequestHandler):
    def get(self):
        results = ConfigFile.all()
        config_files = {}
        for result in results:
            try:
                if config_files[result.name] < result.version:
                    config_files[result.name] = result.version
            except KeyError:
                config_files[result.name] = result.version
        sorted_files = sorted(
            config_files.items(), lambda x, y: cmp(x[0], y[0]))
        self.template_render("list", {'config_files':sorted_files})

class CheckVersion(BaseRequestHandler):
    def get(self):
        name = self.request.get('name')
        if name == '':
            self.errormsg("Name is required")
        else:
            try:
                config_file = ConfigFile.get_latest_version(name)
            except IndexError:
                self.errormsg("Config file does not exist")
                return
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write(config_file.version)

class SendStats(BaseRequestHandler):
    def post(self):
        params = {
            'client_id': self.request.get('client_id'),
            'hit_rate': self.request.get('hit_rate'),
            'cache_size': self.request.get('cache_size')
        }

        # All parameters are required
        for v in params.values():
            if not v:
                self.response.out.write(
                    "FAILED: some parameters were missing\n")
                return

        # Convert types
        try:
            params['hit_rate'] = float(params['hit_rate'])
            params['cache_size'] = int(params['cache_size'])
        except ValueError:
            self.response.out.write(
                "FAILED: stats were not of the correct type\n")
            return

        # Check client ID format
        try:
            uuid.UUID(params['client_id'])
        except ValueError:
            self.response.out.write("FAILED: client ID (must be a UUID)\n")
            return

        entry = CacheStats(**params)
        entry.put()

        self.response.out.write("OK\n")

    def get(self):
        # Allow the use of GET as well as POST, mostly for testing purposes
        self.post()

class GetStats(BaseRequestHandler):
    def get(self):
        params = {
            'client_id': self.request.get('client_id'),
            'date': self.request.get('date', str(int(time.time() - 604800)))
        }

        # All parameters are required
        for v in params.values():
            if not v:
                self.response.out.write(
                    "FAILED: some parameters were missing\n")
                return

        # Check client ID format
        try:
            uuid.UUID(params['client_id'])
        except ValueError:
            self.response.out.write("FAILED: client ID (must be a UUID)\n")
            return

        stats_entries = CacheStats.gql("""WHERE client_id = :client_id
                                       and date >= :date""",
                                        client_id=params['client_id'],
                                        date=datetime.datetime.fromtimestamp(
                                        int(params['date'])))
        self.response.out.write(json.dumps([{
            'date': int(i.date.strftime("%s")),
            'hit_rate': i.hit_rate,
            'cache_size': i.cache_size
        } for i in stats_entries]))

def main():
    url_map = [
        ('/', IndexPage),
        ('/fetch', FetchConfigFile),
        ('/store', StoreConfigFile),
        ('/list', ListFiles),
        ('/check', CheckVersion),
        ('/sendstats', SendStats),
        ('/getstats', GetStats)
    ]
    application = webapp.WSGIApplication(url_map, debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
