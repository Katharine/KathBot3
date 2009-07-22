from datetime import datetime
import modules

channels = {}

def init():
    add_hook('join', join)
    add_hook('332', initial_topic)
    add_hook('topic', topic)
    add_hook('353', userlist)
    add_hook('part', part)
    add_hook('kick', kick)
    add_hook('quit', quit)
    add_hook('nick', nick)

def network(irc):
    if not channels.get(irc.network.name):
        channels[irc.network.name] = {}
    return channels[irc.network.name]

def join(irc, origin, args):
    channel = args[0].lower()
    if origin.nick == irc.nick:
        network(irc)[channel] = Channel(name=channel)
        network(irc)[channel].users[origin.nick.lower()] = origin.nick
        logger.info("Added channel %s/%s" % (irc.network, channel))
        modules.call_hook('joined', irc, channel)
    else:
        network(irc)[channel].users[origin.nick.lower()] = origin.nick
        logger.info("Added nick %s to %s/%s" % (origin.nick, irc.network, channel))

def initial_topic(irc, origin, args):
    channel = args[1].lower()
    network(irc)[channel].topic = args[2]
    logger.info('Set topic for %s/%s to "%s"' % (irc.network, channel, args[2]))

def topic(irc, origin, args):
    channel = args[0].lower()
    topic = args[1]
    network(irc)[channel].topic = topic
    logger.info('Updated topic for %s/%s to "%s"' % (irc.network, channel, topic))

def userlist(irc, origin, args):
    channel_name = args[2].lower()
    channel = network(irc)[channel_name]
    nicks = args[3].split(' ')
    for nick in nicks:
        nick = nick.lstrip('+%@~&^!')
        channel.users[nick.lower()] = nick
        logger.info("Added nick %s to %s/%s" % (nick, irc.network, channel))

def part(irc, origin, args):
    channel = args[0].lower()
    if irc.nick == origin.nick:
        del network(irc)[channel]
        logger.info("Removed channel %s/%s" % (irc.network, channel))
        modules.call_hook('parted', irc, channel)
    else:
        del network(irc)[channel].users[origin.nick.lower()]
        logger.info("Removed nick %s from %s/%s" % (origin.nick, irc.network, channel))

def kick(irc, origin, args):
    channel = args[0].lower()
    nick = args[1].lower()
    if nick == irc.nick.lower():
        del network(irc)[channel]
        logger.info("Removed channel %s/%s" % (irc.network.name, channel))
        modules.call_hook('parted', irc, channel)
    else:
        del network(irc)[channel].users[nick]
        logger.info("Removed nick %s from %s/%s" % (nick, irc.network, channel))

def quit(irc, origin, args):
    if origin.nick == irc.nick:
        return
    nick = origin.nick.lower()
    for channel_name in network(irc):
        channel = network(irc)[channel_name]
        if channel.users.get(nick):
            del channel.users[nick]
            logger.info("Removed nick %s from %s/%s" % (origin.nick, irc.network, channel))

def nick(irc, origin, args):
    newnick = args[0]
    if origin.nick == irc.nick:
        irc.nick = newnick
    else:
        for channel_name in network(irc):
            channel = network(irc)[channel_name]
            if channel.users.get(origin.nick.lower()):
                channel.users[newnick.lower()] = newnick
                del channel.users[origin.nick.lower()]
                logger.info("Renamed %s to %s in %s/%s" % (origin.nick, newnick, irc.network, channel))

# Information access

def nick_channels(irc, nick):
    channels = []
    for channel_name in network(irc):
        channel = network(irc)[channel_name]
        if nick.lower() in channel.users:
            channels.append(channel_name)
    
    return channels

class Channel:
    users = None
    topic = ''
    joined = None
    name = ''
    
    def __init__(self, name='', topic=''):
        self.users = {}
        joined = datetime.now()
        self.name = name
        self.topic = topic
        
    def __str__(self):
        return self.name