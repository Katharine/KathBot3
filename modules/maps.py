# encoding=utf-8
#
#Davy 8-20-09

import htmlentitydefs
import simplejson
import urllib2
import urllib
import sys
import re


#!--vv-Credit to http://effbot.org/zone/re-sub.htm#unescape-html-vv--!#
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text
    return re.sub("&#?\w+;", fixup, text)
#!--^^-Credit to http://effbot.org/zone/re-sub.htm#unescape-html-^^--!#

#API key is valid for http://davykitty.co.uk/ and subdirectories.
APIKEY = """ABQIAAAANJtILwkFMxTl-uwKis6wThRQA87LjK88aEL36WP5Mh6jbitwvhTFH2nL7nivseQvLVBP7vLu0KJWPQ"""

class BaseAddress:
    def __init__(self, address):
        self.query = urllib.urlencode({'q': address})
        self.url = 'http://maps.google.com/maps/geo?%s&output=json&oe=utf8\&sensor=false&key=%s' % (self.query, APIKEY)

class BaseDirections:
    def __init__(self, method, fromquery, toquery):
        self.query = urllib.urlencode({'q': 'from: %s to: %s' % (fromquery, toquery)})
        self.method = method
        self.url = 'http://maps.google.com/maps/nav?%s&doflg=ptj&dirflg=%s&key=%s' % (self.query, method, APIKEY)

def getresponse(irc, target, url):
    try:
        request = urllib2.Request(url, None, {'Referer': 'http://davykitty.co.uk/'})
        return urllib2.urlopen(request)
    except urllib2.HTTPError, error:
        m('irc_helpers').message(irc, target, '~B[Maps]~B Error opening URL: ~B%s~B' % error)
        return

def init():
    add_hook('message', message)

COMMANDS = frozenset(('locationinfo', 'distance', 'time', 'directions'))
methods = {'WALKING': 'w', 'DRIVING': 'd', 'TRANSIT': 't'}
reversemethods = {'d':'Driving','w':'Walking','t':'Transit'}

def message(irc, channel, origin, command, args):
    if command not in COMMANDS:
        return
    irc_helpers = m('irc_helpers')
    target = channel
    
    if command == 'locationinfo':
        #Example Input:
        #!addressinfo 19 Scott Road, Prospect, CT, 06712
        if len(args) < 1:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Not enough arguments - ~BExample Input: \"!mapinfo 'Address'\"")
            return
        
        request = BaseAddress(' '.join(args))
        url = request.url
        response = simplejson.load(getresponse(irc, target, url))
        
        name = response['name']
        try:
            Placemark = response['Placemark'][0]
        except KeyError:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Could not resolve waypoints.")
            return
        ExtendedData = Placemark['ExtendedData']
        Point = Placemark['Point']
        
        address = Placemark['address']
        Accuracy = Placemark['AddressDetails']['Accuracy']
        AdministrativeAreaName = Placemark['AddressDetails']['Country']['AdministrativeArea']['AdministrativeAreaName']
        try:
            LocalityName = Placemark['AddressDetails']['Country']['AdministrativeArea']['Locality']['LocalityName']
            PostalCodeNumber = Placemark['AddressDetails']['Country']['AdministrativeArea']['Locality']['PostalCode']['PostalCodeNumber']
        except:
            try:
                LocalityName = Placemark['AddressDetails']['Country']['AdministrativeArea']['SubAdministrativeArea']['SubAdministrativeAreaName']
                PostalCodeNumber = Placemark['AddressDetails']['Country']['AdministrativeArea']['SubAdministrativeArea']['PostalCode']['PostalCodeNumber']
            except:
                LocalityName = 'UNKNOWN'
                PostalCodeNumber = 'UNKNOWN'
        try:
            ThoroughfareName = Placemark['AddressDetails']['Country']['AdministrativeArea']['Locality']['Thoroughfare']['ThoroughfareName']
        except:
            try:
                ThoroughfareName = Placemark['AddressDetails']['Country']['AdministrativeArea']['SubAdministrativeArea']['Thoroughfare']['ThoroughfareName']
            except:
                ThoroughfareName = 'UNKNOWN'
        CountryName = Placemark['AddressDetails']['Country']['CountryName']
        CountryNameCode = Placemark['AddressDetails']['Country']['CountryNameCode']
        
        north = ExtendedData['LatLonBox']['north']
        south = ExtendedData['LatLonBox']['south']
        east = ExtendedData['LatLonBox']['east']
        west = ExtendedData['LatLonBox']['west']
        
        X = Point['coordinates'][0]
        Y = Point['coordinates'][0]
        Z = Point['coordinates'][0]
        
        irc_helpers.message(irc, target,"~B[Maps] Location Information(Closest Estimate):~B")
        irc_helpers.message(irc, target,"~B[Maps] Address:~B %s" % address)
        irc_helpers.message(irc, target,"~B[Maps] Country:~B %s(%s)" % (CountryName, CountryNameCode))
        irc_helpers.message(irc, target,"~B[Maps] Administrative Area Name:~B %s" % AdministrativeAreaName)
        irc_helpers.message(irc, target,"~B[Maps] Locality:~B %s" % LocalityName)
        irc_helpers.message(irc, target,"~B[Maps] Thoroughfare:~B %s" % ThoroughfareName)
        irc_helpers.message(irc, target,"~B[Maps] Postal Code:~B %s" % PostalCodeNumber)
        irc_helpers.message(irc, target,"~B[Maps] Lat/Lon:~B North: %s -- South: %s -- East: %s -- West: %s" % (north, south, east, west))
        
    elif command == 'distance':
        #Example Input:
        #!distance Walking 19 Scott Road, Prospect, CT, 06712 to 19 Scott Road, Prospect, CT, 06712
        if len(args) < 4:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Not enough arguments - ~BExample Input: \"!distance Method Address1 to Address2\", where 'method' is 'Walking', 'Driving', or 'Transit'")
            return
        
        method = args.pop(0).upper().strip()
        args = ' '.join(args)
        args = args.split(" to ")
        if method in methods:
            method = methods[method]
        else:
            method = 'd'
        request = BaseDirections(method, args[0], args[1])
        url = request.url
        response = simplejson.load(getresponse(irc, target, url))
        
        name = response['name']
        try:
            Placemark = response['Placemark'][0]
        except KeyError:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Could not resolve waypoints.")
            return
        Directions = response['Directions']
        Distance = '%s (%sm)' % (unescape(Directions['Distance']['html']), Directions['Distance']['meters'])
        Duration = Directions['Duration']['html']
        Accuracy = Placemark['AddressDetails']['Accuracy']
        irc_helpers.message(irc, target,"~B[Maps]~B A %s trip from '%s' to '%s' would cover an estimated %s." % (method, args[0], args[1], Distance))
        
    elif command == 'traveltime':
        #Example Input:
        #!time Walking '19 Scott Road, Prospect, CT, 06712' '19 Scott Road, Prospect, CT, 06712'
        if len(args) < 1:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Not enough arguments - ~BExample Input: \"!time Method Address1 to Address2\", where 'method' is 'Walking', 'Driving', or 'Transit'")
            return
        method = args.pop(0).upper().strip()
        args = ' '.join(args)
        args = args.split(" to ")
        if method in methods:
            method = methods[method]
        else:
            method = 'd'
        request = BaseDirections(method, args[0], args[1])
        url = request.url
        response = simplejson.load(getresponse(irc, target, url))
        
        name = response['name']
        try:
            Placemark = response['Placemark'][0]
        except KeyError:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Could not resolve waypoints.")
            return
        Directions = response['Directions']
        Distance = '%s (%sm)' % (unescape(Directions['Distance']['html']), Directions['Distance']['meters'])
        Duration = Directions['Duration']['html']
        
        if method in reversemethods:
            method = reversemethods[method]
        else:
            method = 'Driving'
        irc_helpers.message(irc, target,"~B[Maps]~B A %s trip from '%s' to '%s' would take an estimated %s" % (method, args[0], args[1], Duration))
    elif command == 'directions':
        #Example Input:
        #!directions Walking 19 Scott Road, Prospect, CT, 06712 to 19 Scott Road, Prospect, CT, 06712
        if len(args) < 4:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Not enough arguments - ~BExample Input: \"!directions Method Address1 to Address2\", where 'method' is 'Walking', 'Driving', or 'Transit'")
            return
        
        method = args.pop(0).upper().strip()
        args = ' '.join(args)
        args = args.split(" to ")
        if method in methods:
            method = methods[method]
        else:
            method = 'd'
        request = BaseDirections(method, args[0], args[1])
        url = request.url
        response = simplejson.load(getresponse(irc, target, url))
        
        name = response['name']
        try:
            Placemark = response['Placemark'][0]
        except KeyError:
            irc_helpers.message(irc, target,"~B[Maps]~B ~BError: Could not resolve waypoints.")
            return
        Directions = response['Directions']
        Distance = '%s (%sm)' % (unescape(Directions['Distance']['html']), Directions['Distance']['meters'])
        Duration = Directions['Duration']['html']
        Steps = Directions['Routes'][0]['Steps']
        Accuracy = Placemark['AddressDetails']['Accuracy']
        if method in reversemethods:
            method = reversemethods[method]
        else:
            method = 'Driving'
        irc_helpers.message(irc, target, '~B[Maps]~B %s directions from ~B%s~B to ~B%s~B:' % (method, args[0], args[1]))
        irc_helpers.message(irc, target, '~B[Maps] Number of Steps:~B %s' % len(Steps))
        irc_helpers.message(irc, target, '~B[Maps] Estimated Distance:~B %s' % Distance)
        irc_helpers.message(irc, target, '~B[Maps] Estimated Time:~B %s' % Duration)
        refurl = 'http://maps.google.com/maps?f=d&source=s_d&%s&%s&hl=en&geocode=&mra=ls&%s&sll=37.0625,-95.677068&sspn=40.137381,74.794922&ie=UTF8&z=5' % (urllib.urlencode({'saddr': args[0]}),urllib.urlencode({'daddr': args[1]}),urllib.urlencode({'dirflg': methods[method.upper()]}))
        irc_helpers.message(irc, target, '~B[Maps] For complete [and visual] directions, see: %s' % refurl)
        