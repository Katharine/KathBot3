from datetime import datetime
import modules
import networks

channels = {}

def init():
    add_hook('join', join)
    add_hook('332', initial_topic)
    add_hook('topic', topic)
    add_hook('353', userlist)
    add_hook('319', channel_list)
    add_hook('302', userhosts)
    add_hook('part', part)
    add_hook('kick', kick)
    add_hook('quit', quit)
    add_hook('nick', nick)
    
    for network in networks.networks:
        irc = networks.networks[network]
        if irc.connected:
            irc.raw("WHOIS %s" % irc.nick)

def channel_list(irc, origin, args):
    if args[1] == irc.nick:
        channels = [x.lstrip('@+') for x in args[2].split(' ')]
        for channel in channels:
            irc.raw("NAMES %s" % channel)

def userhosts(irc, origin, args):
    data = args[1].split(' ')
    for datum in data:
        datum = datum.split('=', 1)
        nick = datum[0].rstrip('*')
        hostmask = datum[1].lstrip('+-').split('@', 1)
        ident = hostmask[0]
        host = hostmask[1]
        channels = nick_channels(irc, nick)
        if channels:
            logger.info("Updated ident/host for %s" % nick)
            for channame in channels:
                channel = network(irc)[channame]
                user = channel.users[nick.lower()]
                user.ident = ident
                user.hostname = host
            

def network(irc):
    if not channels.get(irc.network.name):
        channels[irc.network.name] = {}
    return channels[irc.network.name]

def join(irc, origin, args):
    channel = args[0].lower()
    if origin.nick == irc.nick:
        network(irc)[channel] = Channel(name=channel)
        logger.info("Added channel %s/%s" % (irc.network, channel))
        modules.call_hook('joined', irc, channel)
    else:
        logger.info("Added nick %s to %s/%s" % (origin.nick, irc.network, channel))
    user = create_user(irc, origin.nick)
    network(irc)[channel].users[origin.nick.lower()] = user
    if not user.hostname:
        irc.raw("USERHOST %s" % origin.nick)
    

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
    if channel_name not in network(irc):
        network(irc)[channel_name] = Channel(name=args[2])
    channel = network(irc)[channel_name]
    nicks = args[3].split(' ')
    lookup = []
    for nick in nicks:
        nick = nick.lstrip('+%@~&^!')
        user = create_user(irc, nick)
        channel.users[nick.lower()] = user
        if not user.hostname:
            lookup.append(nick)
        logger.info("Added nick %s to %s/%s" % (nick, irc.network, channel))
    if lookup:
        irc.raw("USERHOST %s" % ' '.join(lookup))

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
                channel.users[newnick.lower()] = channel.users[origin.nick.lower()]
                channel.users[newnick.lower()].nick = newnick
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

def create_user(irc, nick):
    existing = nick_channels(irc, nick)
    user = User(nick=nick)
    if existing:
        existing = network(irc)[existing[0]].users[nick.lower()]
        user.ident = existing.ident
        user.hostname = existing.hostname
    return user

class Channel(object):
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

class User(object):
    nick = ''
    hostname = ''
    modes = ''
    ident = ''
    
    def __init__(self, nick='', hostname='', modes='', ident=''):
        self.nick = nick
        self.hostname = hostname
        self.modes = modes
        self.ident = ident
    
    def __str__(self):
        return '%s!%s@%s' % (self.nick, self.ident, self.hostname)