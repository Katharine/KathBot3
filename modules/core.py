# encoding=utf-8
import modules
import threading
import networks

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
    try:
        irc_helpers = m('irc_helpers')
    except:
        logger.warn("Couldn't load irc_helpers.")
    target = args[0]
    args = args[1].split(' ')
    if args[0] == "KB3" and len(args) >= 2:
        command = args[1].lower()
        try:
            if not m('security').check_action_permissible(origin, "kb3:%s" % command):
                irc_helpers.message(irc, target, "You do not have the required access level to do this.")
                return
        except ModuleNotLoaded:
            pass
        
        args = args[2:]
        if command == 'ping':
            irc_helpers.message(irc, target, "PONG!")
        elif command == 'load':
            for module in args:
                try:
                    modules.load_module(module)
                except Exception, msg:
                    irc_helpers.message(irc, target, "Couldn't load %s: %s." % (module, msg))
                else:
                    irc_helpers.message(irc, target, "Loaded %s" % module)
        elif command == 'unload':
            for module in args:
                try:
                    modules.unload_module(module)
                    irc_helpers.message(irc, target, "Unloaded %s" % module)
                except ModuleNotLoaded:
                    irc_helpers.message(irc, target, "Couldn't unload %s; it's not loaded." % module)
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
        elif command == 'threads':
            threads = u' · '.join(sorted(['~B%s~B: %s' % (x.__class__.__name__, x.getName()) for x in threading.enumerate()]))
            irc_helpers.message(irc, target, '~B[THREADING]~B %s' % threads)
        elif command == 'modules':
            mod = u' · '.join(sorted(modules.mods.keys()))
            irc_helpers.message(irc, target, '~B[Modules]~B %s' % mod)
        elif command == 'terminate':
            reason = ''
            if len(args) > 0:
                reason = ' '.join(args)
            module_list = modules.mods.keys()
            for module in module_list:
                modules.unload_module(module)
            
            for network in networks.networks:
                networks.networks[network].disconnect(reason=reason)         

# Other useful "core"-like methods.

def check_prefix(line):
    if line.startswith("!"):
        return line[1:]
    return None