# encoding=utf-8
#
#Davy 7-20-10
#Kitty 7-21-10 - altered to use YouTube's GData API instead of screen scraping.

from __future__ import division
import urllib2
import xml.dom.minidom as dom
import re
import textwrap

def init():
    add_hook('privmsg', privmsg)

def privmsg(irc, origin, args):
    message = args[1]
    channel = args[0]
    if "http://www.youtube.com/watch" in message:
        message = message[message.find("http://www.youtube.com/watch"):]
        url = message
        if ' ' in message:
            url = message[0:message.find(' ')]
        video_id = re.search("v=([^&]+)", url)
        if video_id is None:
            return
        video_id = video_id.group(1)
        response = urllib2.urlopen('http://gdata.youtube.com/feeds/api/videos/%s' % video_id)
        xml = dom.parse(response)
        response.close()
        user = xml.getElementsByTagName('author')[0].getElementsByTagName('name')[0].firstChild.data
        title = xml.getElementsByTagName('title')[0].firstChild.data
        desc = xml.getElementsByTagName('media:description')[0].firstChild.data.split("\n")[0]
        if len(desc) > 100:
            desc = textwrap.wrap(desc, 97)[0] + "..."
        length = int(xml.getElementsByTagName('yt:duration')[0].getAttribute('seconds'))
        
        xml.unlink()
        
        mins = length // 60
        secs = length % 60
        m('irc_helpers').message(irc, channel, u"~BTitle:~B %s · ~BLength:~B %s:%s · ~BUploader:~B %s\n~BDescription:~B %s" % (title, mins, secs, user, desc), tag='Video')
