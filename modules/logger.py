import os
import os.path
import datetime

def init():
    add_hook('mode', mode)
    add_hook('privmsg', privmsg)
    add_hook('join', join)
    add_hook('part', part)
    add_hook('quit', quit)
    add_hook('kick', kick)
    add_hook('topic', topic)
    add_hook('nick', nick)

def writeline(network, channel, line):
    network = network.replace('/', '_')
    channel = channel.replace('/', '_')
    if not os.path.exists("data/logs/%s" % network):
        os.mkdir("data/logs/%s" % network)
    f = open("data/logs/%s/%s.log" % (network, channel), 'a')
    f.write("[%s] %s\n" % (datetime.datetime.utcnow().strftime('%m/%d/%Y %H:%M:%S'), line))
    f.close()

def privmsg(irc, origin, args):
    channel = args[0]
    message = args[1]
    if channel[0] == '#':
        if message.startswith('\x01ACTION ') and message.endswith('\x01'):
            writeline(irc.network.name, channel, "** %s %s" % (origin.nick, message[8:-1]))
        else:
            writeline(irc.network.name, channel, "<%s> %s" % (origin.nick, message))

def join(irc, origin, args):
    writeline(irc.network.name, args[0], "* %s (%s) has joined %s" % (origin.nick, origin.hostname, args[0]))

def part(irc, origin, args):
    channel = args[0]
    if len(args) > 1:
        reason = " (%s)" % args[1]
    else:
        reason = ''
    writeline(irc.network.name, args[0], "* %s has left %s%s" % (origin.nick, channel, reason))

def topic(irc, origin, args):
    writeline(irc.network.name, args[0], "* %s changes topic to '%s'" % (origin.nick, args[1]))

def kick(irc, origin, args):
    writeline(irc.network.name, args[0], "* %s was kicked by %s (%s)" % (args[1], origin.nick, args[2]))

def mode(irc, origin, args):
    writeline(irc.network.name, args[0], "* %s sets mode: %s" % (origin.nick, ' '.join(args[1:])))

def quit(irc, origin, args):
    if len(args) > 0:
        reason = " (%s)" % args[0]
    else:
        reason = ''
    for channel in m('chantrack').nick_channels(irc, origin.nick):
        writeline(irc.network.name, channel, "* %s (%s) Quit%s" % (origin.nick, origin.hostname, reason))

def nick(irc, origin, args):
    newnick = args[0]
    # We don't know if we'll come before or after chantrack updates,
    # so handle both cases.
    channels = m('chantrack').nick_channels(irc, origin.nick)
    if len(channels) == 0:
        channels = m('chantrack').nick_channels(irc, newnick)
    
    for channel in channels:
        writeline(irc.network.name, channel, "* %s is now known as %s" % (origin.nick, newnick))
