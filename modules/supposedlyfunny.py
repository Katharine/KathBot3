import xml.dom.minidom as dom
import urllib2
from locale import format as format_number
from datetime import datetime
from xml.sax.saxutils import unescape
import re
import random
from subprocess import Popen, PIPE, STDOUT

COMMANDS = frozenset(('fml', 'bash', 'fortune'))

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command not in COMMANDS:
        return
    irch = m('irc_helpers')
    if command == 'fml':
        url = 'http://api.betacie.com/view/random/nocomment?key=readonly&language=en'
        if len(args) == 1:
            try:
                fmlid = int(args[0])
                url = 'http://api.betacie.com/view/%s/nocomment?key=readonly&language=en' % fmlid
            except:
                pass
        try:
            f = urllib2.urlopen(url)
            xml = f.read()
            f.close()
            xml = dom.parseString(xml)
            item = xml.getElementsByTagName('item')[0]
            author = item.getElementsByTagName('author')[0].firstChild.data
            content = item.getElementsByTagName('text')[0].firstChild.data
            fmlid = item.getAttribute('id')
            agree = int(item.getElementsByTagName('agree')[0].firstChild.data)
            deserved = int(item.getElementsByTagName('deserved')[0].firstChild.data)
            #published = datetime.strptime(item.getElementsByTagName('date')[0].firstChild.data[:-6], '%Y-%m-%dT%H:%M:%S')
        except:
            irch.message(irc, channel, "Couldn't load item.")
            return
        
        irch.message(irc, channel, "~B[FML]~B ~UFML ~B#%s~B from ~B%s~B~U" % (fmlid, author))
        irch.message(irc, channel, "~B[FML]~B %s" % content)
        irch.message(irc, channel, "~B[FML]~B Agree: ~B%s~B | Disagree: ~B%s~B" % (format_number('%i', agree, True), format_number('%i', deserved, True)))
    elif command == 'bash':
        # With thanks to Davy. <3
        try:
            f = urllib2.urlopen('http://www.bash.org/?random1')
            data = f.read()
            f.close()
            quotes = re.findall('<p class="quote"><a href="(.+?)".*?</p><p class="qt">(.+?)</p>', data, re.S)
            quote = random.choice(quotes)
            lines = unescape(quote[1].replace('<br />','')).split('\n')
        except urllib2.HTTPError:
            irch.message(irc, channel, "~B[bash]~B Couldn't find a quote. D:")
            return
        irch.message(irc,channel,'~B[bash]~B ~UFrom: http://www.bash.org/%s~U' % quote[0])
        for line in lines:
            irch.message(irc, channel, '~B[bash]~B %s' % line)
    elif command == 'fortune':
        command = ["fortune"]
        if len(args) > 0:
            command.append(args[0])
        irch.message(irc, channel, Popen(command, stdout=PIPE, stderr=STDOUT).communicate()[0].rstrip().replace("\t", "    "), tag="Fortune")
