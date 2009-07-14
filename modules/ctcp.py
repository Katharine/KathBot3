import time
import sys
import datetime
from subprocess import Popen, PIPE

def init():
    add_hook('privmsg', privmsg)

def respond(irc, nick, message):
    m('irc_helpers').notice(irc, nick, '\x01%s\x01' % message)

def privmsg(irc, origin, args):
    if args[0] != irc.nick:
        return
    
    nick = origin.nick
    message = args[1]
    if message[0] == '\x01' and message[-1] == '\x01':
        args = message[1:-1].split(' ')
        command = args.pop(0).upper()
        if command == 'PING':
            if len(args) > 0:
                respond(irc, nick, 'PING %s' % args[0])
            else:
                respond(irc, nick, 'PING %s' % int(time.time()))
        elif command == 'VERSION':
            respond(irc, nick, 'VERSION KathBot3, python %s' % sys.version.replace("\n", " "))
        elif command == 'SOURCE':
            respond(irc, nick, 'SOURCE http://katharine.svn.beanstalkapp.com/kathbot/')
        elif command == 'CLIENTINFO':
            respond(irc, nick, 'VERSION SOURCE PING CLIENTINFO ACTION FINGER TIME')
        elif command == 'FINGER':
            respond(irc, nick, 'FINGER I be a robot!')
        elif command == 'TIME':
            respond(irc, nick, 'TIME %s' % datetime.datetime.now().strftime('%a, %d %b %Y %H:%M %z'))
        elif command == 'GESTALT':
            respond(irc, nick, 'GESTALT %s' % Popen(["uptime"], stdout=PIPE).communicate()[0].strip())