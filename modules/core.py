import modules

def init():
    add_hook('ping', ping)
    add_hook('error', server_disconnect)
    add_hook('001', connected)
    add_hook('privmsg', privmsg)

def ping(irc, origin, args):
    irc.raw("PONG :%s" % args[0])
    
def server_disconnect(irc, origin, args):
    irc.disconnect(forced=True)
    logger.error("Disconnected from %s" % irc.network.server)

def connected(irc, origin, args):
    if irc.network.primary_channel:
        m('irc_helpers').join(irc, irc.network.primary_channel)
    
    modules.call_hook('connected', irc)
    logger.info("Completed connecting to %s" % irc.network.server)

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target = args[0]
    args = args[1].split(' ')
    if args[0] == "KB3" and len(args) >= 2:
        command = args[1].lower()
        if m('security'):
            if not m('security').check_action_permissible(origin, "kb3:%s" % command):
                irc_helpers.message(irc, target, "You do not have the required access level to do this.")
                return
        
        args = args[2:]
        if command == 'ping':
            irc_helpers.message(irc, target, "PONG!")
        elif command == 'load':
            for module in args:
                try:
                    modules.load_module(module)
                except Exception, msg:
                    irc_helpers.message(irc, target, "Couldn't load %s: %s" % (module, msg))
                else:
                    irc_helpers.message(irc, target, "Loaded %s" % module)
        elif command == 'unload':
            for module in args:
                modules.unload_module(module)
                irc_helpers.message(irc, target, "Unloaded %s" % module)
        elif command == 'reload':
            for module in args:
                try:
                    modules.unload_module(module)
                    modules.load_module(module)
                except Exception, msg:
                    irc_helpers.message(irc, target, "Couldn't reload %s: %s" % (module, msg))
                else:
                    irc_helpers.message(irc, target, "Reloaded %s" % module)
        elif command == 'raw':
            irc.raw(' '.join(args))
            irc_helpers.message(irc, target, "Sent message.")
        elif command == 'terminate':
            quit()

# Other useful "core"-like methods.

def check_prefix(line):
    if line.startswith("!"):
        return line[1:]
    return None