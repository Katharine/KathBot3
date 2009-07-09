# Note that this module assumes use of a hacked pisg.

import os
import subprocess
import threading

PISG_OUTPUT = "/home/katharine/web/irc.ajaxlife.net/stats/"
PISG_WEB_URL = "http://irc.ajaxlife.net/stats/%s/%s.html"

def run_pisg(network, channel, irc=None):
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

def pisg(network, channel, irc=None):
    thread = threading.Thread(target=run_pisg, name="pisg-manual-%s-%s" % (network, channel), args=(network, channel), kwargs={'irc': irc})
    thread.start()

def init():
    add_hook('privmsg', privmsg)

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if command == 'stats':
        pisg(irc.network.name, target, irc)