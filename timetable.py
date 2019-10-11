#!/usr/bin/python3

DESCRIPTION = '''
Simple little bus stop timetable for stockholms lokaltrafik, could easily be used for other transport types.
Use with settings file and get you own API keys from sl.se trafiklab. Also simple lookup of stops with '-l'
'''

from urllib import parse, request
import sys
import time
import datetime
import json
import os
import pwd
import shelve
import argparse


UA="Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0"
BASEDIR = '.whenisnext'
STORENAME = 'store'
SETTINGSFILE = 'settings'
DATAPATH = os.path.join(os.path.expanduser('~' + pwd.getpwuid(os.getuid()).pw_name), BASEDIR, STORENAME)
SETTINGSPATH = os.path.join(os.path.expanduser('~' + pwd.getpwuid(os.getuid()).pw_name), BASEDIR, SETTINGSFILE)

#realtidsinfo
TRANSPORTMODES = ('Buses','Metros', 'Trains', 'Trams', 'Ships')
REALTIMEVERSION = 'V4'
REALTIMEURL = 'http://api.sl.se/api2/realtimedepartures{}.json?'.format(REALTIMEVERSION)
PLATSUPPSLAGURL = 'https://api.sl.se/api2/typeahead.json?'

exampleconfig = '''
TRANSPORTMODE = 'Buses'
LINENO = '2'
DESTINATION = 'Sofia'
CACHETIME = 330
REALTIMEKEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
STATIONID = 1073
'''

# read settings
try:
    exec(open(SETTINGSPATH).read())
except FileNotFoundError as err:
    print('\nMissing configuration create "{}" like so:\n{}\n'.format(SETTINGSPATH, exampleconfig))
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(epilog=DESCRIPTION, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-l', '--lookup', dest='lookup', help='lookup stop',
            default=False)
    args = parser.parse_args()
    return args, parser

def createHttpRequest(url, cookiejar=None):
    urlparts = parse.urlparse(url)
    headers = { 'User-Agent' : UA, 'Referer' : url, 'Cache-Control':  "max-age=0", 
            "Accept-Language": "sv-SE,en;q=0.7,en-US;q=0.3a", "Accept-Encoding":"gzip, deflate",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Pragma": "no-cache"}
    req = request.Request(url, None, headers)
    if cookiejar:
        cookiejar.add_cookie_header(req)
    with request.urlopen(req) as response:
        resp = response.read()
        if response.getheader("Content-Encoding") == "gzip":
            resp = gzip.decompress(resp)
        try:
            charset = response.getheader("Content-Type").split("charset=")[1]
        except:
            charset = guessCharset(resp)

    return (resp, charset)


def cached_data(get=True, value=None):
    d = shelve.open(os.path.join(DATAPATH))
    lastkey = 'lastrecording'
    now = datetime.datetime.now()

    if not get:
        d[lastkey] = (now, value)
        d.close()
        return None

    try:
        lasttime, lastval = d[lastkey]
    except KeyError:
        print('Failed to get cached data') # DEBUG
        return None

    timediff = (now - lasttime).seconds
    if timediff <= CACHETIME:
        return lastval
    else:
        d[lastkey] = (now, value)
        d.close()
    return None

def times_printer(times):
    now = datetime.datetime.now()
    resstring = ''
    for t in times:
        inmins = int((t - now).seconds / 60)
        if not inmins > 1000: # most likely wrapped the day
            timestr = '{} ({} mins); '.format(datetime.datetime.strftime(t, '%H:%M'), inmins)
            resstring += timestr

    resstring = resstring.strip('; ').strip()
    print(resstring)

def get_data():
    lastval = cached_data(get=True, value=None)
    if lastval is not None:
        times_printer(lastval)
        sys.exit(0)
    params = {'key': REALTIMEKEY, 'siteid': STATIONID, 'timewindow': '40'}
    url = REALTIMEURL + parse.urlencode(params)
    result = createHttpRequest(url)
    jsondata = json.loads(result[0])
    resstring = ''

    if TRANSPORTMODE in  jsondata['ResponseData']:
        transports = [tr for tr in jsondata['ResponseData'][TRANSPORTMODE]\
                if tr['Destination'] == DESTINATION and tr['LineNumber'] == LINENO]

        times = [ datetime.datetime.strptime(t['ExpectedDateTime'], '%Y-%m-%dT%H:%M:%S')\
                for t in transports]

        cached_data(get=False, value=times) # set new cache
        times_printer(times)

def lookup(args):
    params = {'searchstring': args.lookup, 'key': PLATSUPPSLAG}
    url = PLATSUPPSLAGURL + parse.urlencode(params)
    result = createHttpRequest(url)
    jsondata = json.loads(result[0])
    for stop in jsondata['ResponseData']:
        print('Name: ', stop['Name'])
        print('Id: ', stop['SiteId'])
        print()

def main():
    args, parser = parse_args()
    if args.lookup:
        lookup(args)
        sys.exit(0)
    get_data()

if __name__ in '__main__':
    main()

# TODO
##platsuppslag
#PLATSUPPSLAGURL = 'https://api.sl.se/api2/typeahead.json?'
#params = {'searchstring': 'Norrtullsgatan', 'key': 'XXXXXXXXXXX'}
#url = PLATSUPPSLAGURL + urllib.parse.urlencode(params)
#result = httpbplate.createHttpRequest(url)
#jsondata = json.loads(result[0])
#jsondata['ResponseData'][0]['Name']
#jsondata['ResponseData'][0]['SiteId']
