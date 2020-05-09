#!/usr/bin/python

import web
import requests
import xmltodict
import json
import os
import sys
import datetime
from collections import OrderedDict
from operator import itemgetter
import utils

urls = ('/', 'index',
        '/help', 'help',
        '/download', 'download'
        )

app = web.application(urls, globals())
render = web.template.render('templates/', base="layout")

# Uncomment to turn debug off
web.config.debug = False

# Variables
output = []

# Functions


def calculate_count(data):
    count = {}
    ls = data.values()
    z, nz = 0, 0
    for v in ls:
        if v == 0:
            z += 1
        else:
            nz += 1
    count['green'] = z
    count['red'] = nz
    return count


def getMonit():
    output = []
    xmlQuery = "/_status?format=xml"

    with open('{0}/conf/servers.json'.format(os.path.expanduser('.'))) as f:
        servers = json.loads(f.read())

        for server in servers:
            host = servers[server]
            
            try:
                response = requests.get(host['url'] + xmlQuery, auth=(host['user'], host['passwd']))
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(err)

            allstat = json.loads(json.dumps(xmltodict.parse(response.text)['monit']))

            services = allstat['service']
            status = {}
            server = {}
            checks = OrderedDict()

            for service in services:
                name = service['name']
                status[name] = int(service['status'])
                checks[name] = status[name]

            sorted_checks = OrderedDict()
            sorted_checks = OrderedDict(sorted(checks.items(), key=itemgetter(1), reverse=True))
            count = calculate_count(sorted_checks)
            server = dict(name=server, url=host['url'], result=sorted_checks, s_rate=count)

            output.append(server)
    print(datetime.datetime.now())
    return(output)

# Classes


class monitDashboard(web.application):
    def run(self, port=8080, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))


class index(object):
    def GET(self):
        return render.index(output=getMonit(),
                            now=datetime.datetime.now())


class help(object):
    def GET(self):
        return render.help()


class download(object):
    def GET(self):
        filename = 'health_report.xlsx'
        output = getMonit()
        utils.generate_report_excel(output, filename)
        web.header('Content-Disposition',
                   'attachment; filename="health_report.xlsx"')
        web.header('Content-type', 'application/octet-stream')
        web.header('Cache-Control', 'no-cache')
        return open(filename, 'rb').read()


# Main
if __name__ == "__main__":
    app = monitDashboard(urls, globals())
    app.run(port=7071)
