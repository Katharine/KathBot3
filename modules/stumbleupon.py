# encoding=utf-8
import urllib
import urllib2
import re
import simplejson

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command == 'stumble':
        headers = {'Cookie': 'PHPSESSID=274vs2g8hl0c5cc74kk7qc0vu6; cmf_i=16302779294a6693d6a90973.54918751; cmf_spr=A%2FN; cmf_sp=http%3A%2F%2Fwww.stumbleupon.com%2F; uid=9efbb9a9b66680361256032e7d577e25-1-0; s_cc=true; s_sq=%5B%5BB%5D%5D; __qca=1248236505-70782580-76549394; __qcb=1969373048'}
        f = urllib2.urlopen(urllib2.Request('http://www.stumbleupon.com/s/', headers=headers))
        data = f.read().decode('utf-8')
        f.close()
        token = re.search("var ftoken = '(.+?)';", data).group(1)
        post = {'action': 'general', 'ftoken': token, 'secondary': 'userdata'}
        request = urllib2.Request('http://www.stumbleupon.com/toolbar/services.php', data=urllib.urlencode(post), headers=headers)
        f = urllib2.urlopen(request)
        parsed = simplejson.load(f)
        f.close()
        m('irc_helpers').message(irc, channel, '~B%s (%s)~B' % (parsed['title'], u'★' * parsed['stars']), tag='StumbleUpon')
        m('irc_helpers').message(irc, channel, parsed['url'], tag='StumbleUpon')
        m('irc_helpers').message(irc, channel, 'Discovered by ~B%s~B | Topic: ~B%s~B | ~B%s~B reviews' % (parsed['discoverer_nick'], parsed['topic'], parsed['numreviews']), tag='StumbleUpon')