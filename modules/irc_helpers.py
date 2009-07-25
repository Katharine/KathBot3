# encoding=utf-8
class PotentialInfiniteLoop(Exception): pass
from htmlentitydefs import name2codepoint
import re
import modules
import textwrap

def format(msg):
    return msg.replace('~B', chr(2)).replace('~U', chr(31)).replace('~I', chr(22))

last_line = ""
uses = 0
def message(irc, target, msg, fmt=True, tag=None):
    global last_line, uses
    if not isinstance(msg, basestring):
        msg = str(msg)
    # Infinite loop?
    if msg == last_line:
        uses += 1
        if uses > 10:
            raise PotentialInfiniteLoop
    else:
        last_line = msg
        uses = 1
    

    
    lines = msg.split("\n")
    pre_B = False
    pre_I = False
    pre_U = False
    for maybe_line in lines:
        if not maybe_line:
            continue
        real_lines = textwrap.wrap(maybe_line, 400)
        for line in real_lines:
            if pre_B:
                line = '~B' + line
            if pre_I:
                line = '~I' + line
            if pre_U:
                line = '~U' + line
            pre_B, pre_I, pre_U = (False, False, False)
            if line.count('~B') % 2 == 1:
                pre_B = True
                line += '~B'
            if line.count('~I') % 2 == 1:
                pre_I = True
                line += '~I'
            if line.count('~U') % 2 == 1:
                pre_U = True
                line += '~U'
            if fmt:
                line = format(line)
            if tag is not None:
                line = '\x02[%s]\x02 %s' % (tag, line)
            elif line.startswith("/me"):
                line = "\x01ACTION %s\x01" % line[4:]
            irc.raw("PRIVMSG %s :%s" % (target, line))

def notice(irc, target, msg, fmt=True):
    if fmt:
        msg = format(msg)
    irc.raw("NOTICE %s :%s" % (target, msg))

def join(irc, channel, passkey=None):
    if passkey:
        irc.raw("JOIN %s %s" % (channel, passkey))
    else:
        irc.raw("JOIN %s" % channel)

def part(irc, channel, reason=""):
    irc.raw("PART %s :%s" % (channel, reason))
    
def parse(args):
    line = m('core').check_prefix(args[1])
    if not line:
        return None, None, None
    
    line = line.split(' ')
    command = line.pop(0)
    return args[0], command, line

def html_to_irc(html):
    # Deal with formatting tags
    irc = re.sub('(?:</(?:b|em|i|strong)>){2}', '</b>', re.sub('(?:<(?:b|em|i|strong)>){2}', '<b>', html))
    irc = re.sub('<br[^>]*>', '\n', re.sub('</?u>', '~U', re.sub('</?(?:b|em|i)>', '~B', irc)))
    # Deal with image tags
    irc = re.sub(r'<img.*?src="(.+?(?:\.png|\.jpg))".*?>', r'\1', irc)
    # Clear left-over tags
    irc = re.sub('<.+?>', '', irc)
    # Deal with entities
    irc = re.sub('&#([0-9]+);?', lambda x: unichr(int(x.group(1))), irc)
    irc = re.sub('&(%s);' % '|'.join(name2codepoint), lambda m: unichr(name2codepoint[m.group(1)]), irc)

    # Deal with newlines
    irc = re.sub('\n+', '\n', irc)
    return irc

# Be helpful and do decoding
def init():
    add_hook('privmsg', privmsg)

def privmsg(irc, origin, args):
    channel, command, args = parse(args)
    if not command:
        return
    try:
        permitted = m('security').check_action_permissible(origin, command)
    except ModuleNotLoaded:
        permitted = True
    if channel == irc.nick:
        channel = origin.nick
    if permitted:
        modules.call_hook('message', irc, channel, origin, command, args)
    else:
        message(irc, channel, "You do not have sufficient access to do this!")