import time

automode = {}
mutes = {}

def init():
    add_hook('connected', connected)
    add_hook('join', join)
    add_hook('message', message)
    
    channels = m('datastore').query("SELECT network, channel, automode FROM channels")
    for channel in channels:
        if not automode.get(channel[0]):
            automode[channel[0].lower()] = {}
        if channel[2] is not None:
            automode[channel[0].lower()][channel[1].lower()] = channel[2]
            logger.info("Set automode for %s to +%s" % (channel[1], channel[2]))

def message(irc, channel, origin, command, args):
    irc_helpers = m('irc_helpers')
    if command == 'chanmode':
        modes = ''
        if len(args) >= 1:
            modes = args[0]
        m('datastore').execute("UPDATE channels SET automode = ? WHERE network = ? AND channel = ?", modes, irc.network.name, channel)
        if irc.network.name.lower() not in automode:
            automode[irc.network.name.lower()] = {}
        automode[irc.network.name.lower()][channel.lower()] = modes
        irc_helpers.message(irc, channel, "Updated automode settings for %s" % channel)
    elif command == 'addchan':
        if len(args) < 1:
            irc_helpers.message(irc, channel, "You need to specify a channel.")
            return
        channel = args[0]
        key = None
        if len(args) > 1:
            key = args[1]
        irc_helpers.join(irc, channel, key)
        m('datastore').execute("INSERT INTO channels(channel, network, passkey) VALUES(?, ?, ?)", channel.lower(), irc.network.name, key)
        irc_helpers.message(irc, channel, "Joined %s." % channel)
    elif command == 'automode':
        if len(args) < 1:
            irc_helpers.message(irc, channel, "You need to specify who you're changing modes for.")
            return
        nick = m('security').get_canonical_nick(args[0])
        uid = m('datastore').query("SELECT id FROM users WHERE nick = ?", nick)
        if len(uid) == 0:
            irc_helpers.message(irc, channel, "Only %s users can have modes." % irc.nick)
            return
        uid = uid[0][0]
        if len(args) > 1:
            modes = args[1]
        else:
            modes = None
        
        m('datastore').execute("REPLACE INTO chanmanage_modes (channel, uid, modes) VALUES (?, ?, ?)", channel.lower(), uid, modes)
        irc.raw("MODE %s +%s %s" % (channel, modes, (nick + " ") * len(modes)))
        irc_helpers.message(irc, channel, "Set mode ~B+%s~B for ~B%s~B in ~B%s~B." % (modes, nick, channel))
    elif command == 'mute':
        modes = automodes(irc.network.name, channel)
        if modes == '':
            irc_helpers.message(irc, channel, "This channel has no automode, so muting makes no sense")
            return
        try:
            nick = args[0]
            period = int(args[1])
        except:
            irc_helpers.message(irc, channel, "Usage: mute [nick] [time]")
            return
        key = '%s/%s' % (irc.network, channel)
        if key not in mutes:
            mutes[key] = set()
        mutes[key].add(nick.lower())
        irc.raw("MODE %s -%s %s" % (channel, modes, (nick + ' ') * len(modes)))
        m('cron').add_at(time.time() + period * 60, unmute, irc, channel, nick)
        irc_helpers.message(irc, channel, "Muted %s for %s minutes." % (nick, period))

def connected(irc):
    channels = m('datastore').query("SELECT channel, passkey FROM channels WHERE network = ?", irc.network.name)
    for channel in channels:
        m('irc_helpers').join(irc, channel[0], channel[1])

def join(irc, origin, args):
    channel = args[0].lower()
    try:
        if origin.nick.lower() in mutes['%s/%s' % (irc.network, channel)]:
            return
    except:
        pass
    modes = automodes(irc.network.name, channel)
    
    uid = m('security').get_user_id(origin)
    if uid is not None:
        user_modes = m('datastore').query("SELECT modes FROM chanmanage_modes WHERE channel = ? AND uid = ?", channel, uid)
        if len(user_modes) > 0 and user_modes[0][0]:
            modes += user_modes[0][0]
    
    irc.raw("MODE %s +%s %s" % (channel, modes, (origin.nick + " ") * len(modes)))

def automodes(network, channel):
    if automode.get(network) and automode[network.lower()].get(channel):
        return automode[network][channel]
    return ''

def unmute(irc, channel, nick):
    key = '%s/%s' % (irc.network, channel)
    if key not in mutes:
        return
    if nick.lower() not in mutes[key]:
        return
    mutes[key].remove(nick.lower())
    modes = automodes(irc.network.name, channel)
    if modes:
        irc.raw("MODE %s +%s %s" % (channel, modes, (nick + ' ') * len(modes)))