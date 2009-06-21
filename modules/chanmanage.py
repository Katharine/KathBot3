automode = {}

def init():
    add_hook('connected', connected)
    add_hook('join', join)
    add_hook('privmsg', privmsg)
    
    channels = m('datastore').query("SELECT network, channel, automode FROM channels")
    for channel in channels:
        if not automode.get(channel[0]):
            automode[channel[0].lower()] = {}
        automode[channel[0].lower()][channel[1].lower()] = channel[2]
        logger.info("Set automode for %s to +%s" % (channel[1], channel[2]))

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if not command:
        return
    if not m('security').check_action_permissible(origin, command):
        irc_helpers.message(irc, target, "You do not have the required access level to do this.")
        return
    if command == 'chanmode':
        modes = ''
        if len(args) >= 1:
            modes = args[0]
        m('datastore').execute("UPDATE channels SET automode = ? WHERE network = ? AND channel = ?", modes, irc.network.name, target)
        automode[irc.network.name.lower()][target.lower()] = modes
        irc_helpers.message(irc, target, "Updated automode settings for %s" % target)
    elif command == 'addchan':
        if len(args) < 1:
            irc_helpers.message(irc, target, "You need to specify a channel.")
            return
        channel = args[0]
        key = None
        if len(args) > 1:
            key = args[1]
        irc_helpers.join(irc, channel, key)
        m('datastore').execute("INSERT INTO channels(channel, network, passkey) VALUES(?, ?, ?)", channel.lower(), irc.network.name, key)

def connected(irc):
    channels = m('datastore').query("SELECT channel, passkey FROM channels WHERE network = ?", irc.network.name)
    for channel in channels:
        m('irc_helpers').join(irc, channel[0], channel[1])

def join(irc, origin, args):
    channel = args[0].lower()
    if automode.get(irc.network.name) and automode[irc.network.name.lower()].get(channel):
        modes = automode[irc.network.name][channel]
        logger.info("Setting +%s on %s in %s" % (modes, origin.nick, channel))
        command = "MODE %s +%s %s" % (channel, modes, " ".join(["%s" % origin.nick for x in range(0, len(modes))]))
        irc.raw(command)
