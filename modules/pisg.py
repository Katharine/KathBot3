# Note that this module assumes use of a hacked pisg.

from __future__ import with_statement
import os
import subprocess
import threading

PISG_OUTPUT = "/home/katharine/web/irc.ajaxlife.net/stats/"
PISG_WEB_URL = "http://irc.ajaxlife.net/stats/%s/%s.html"

def run_pisg(network, channel, irc=None):
    update_nicks()
    if irc is not None:
        m('irc_helpers').message(irc, channel, "Generating stats...")
    if not os.path.exists(PISG_OUTPUT+network):
        os.mkdir(PISG_OUTPUT+network)
    subprocess.check_call([
        'pisg',
        '-co', 'data/pisg/base.cfg',
        '-ne', network,
        '-ch', channel,
        '-o', "%s%s/%s.html" % (PISG_OUTPUT, network.replace('/','_'), channel[1:].replace('/','_')),
        '-l', 'data/logs/%s/%s.log' % (network.replace('/','_'), channel.replace('/','_')),
    ])
    if irc is not None:
        m('irc_helpers').message(irc, channel, "Stats generation completed. You can see them at %s" % (PISG_WEB_URL % (network, channel[1:])))

def update_nicks():
    aliases = m('datastore').query("SELECT alias, canon FROM aliases")
    nicks = {}
    for alias in aliases:
        if alias[1] not in nicks:
            nicks[alias[1]] = StatUser(alias[1])
        nicks[alias[1]].aliases.append(alias[0])
    with open('data/pisg/nicks.cfg', 'w') as f:
        for nick in nicks:
            user = nicks[nick]
            f.write('<user nick="%s" alias="%s">\n' % (nick, ' '.join(user.aliases)))

def pisg(network, channel, irc=None):
    thread = threading.Thread(target=run_pisg, name="pisg-manual-%s-%s" % (network, channel), args=(network, channel), kwargs={'irc': irc})
    thread.start()

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command == 'stats':
        pisg(irc.network.name, channel, irc)

class StatUser(object):
    aliases = None
    nick = ''
    gender = ''
    
    def __init__(self, nick):
        self.nick = nick
        self.aliases = []