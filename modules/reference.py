# encoding=utf-8
import urllib2
import re
from xml.sax.saxutils import escape, unescape
import random
import textwrap
import simplejson as json
import aspell

COMMANDS = frozenset(('google', 'wikipedia', 'wiki', 'define', 'translate', 'spell',))

# Various UAs from Safari's Develop menu.
USER_AGENTS = (
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_7; en-us) AppleWebKit/530.17 (KHTML, like Gecko) Version/4.0 Safari/530.17',
    'Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)',
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.10) Gecko/2009042315 Firefox/3.0.10',
    'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10',
    'Opera/9.64 (Macintosh; Intel Mac OS X; U; en) Presto/2.1.1',
    'Opera/9.64 (Windows NT 6.0; U; en) Presto/2.1.1',
)

def load_url(url):
    handle = urllib2.urlopen(urllib2.Request(url, headers={'User-Agent': random.choice(USER_AGENTS), 'Referrer': 'http://kathar.in'}))
    data = handle.read().decode('utf-8')
    handle.close()
    return data

# Because urllib's doesn't like multibyte unicode.
def escapeurl(url):
    safe = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
    output = ''
    for char in url:
        if char in safe:
            output += char
        else:
            code = hex(ord(char))[2:]
            while len(code) > 0:
                if len(code) == 1:
                    code = '0' + code
                output += '%' + code[0:2]
                code = code[2:]
    return output

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    if command not in COMMANDS:
        return
    irch = m('irc_helpers')
    format = irch.html_to_irc
    if command == 'google':
        if len(args) == 0:
            irch.message(irc, channel, "~B[Google]~B Please supply a search query.")
            return
        search = ' '.join(args)
        try:
            data = load_url('http://www.google.com/search?hl=en&q=%s&aq=f&oq=&aqi=g10' % escapeurl(search))
            result = re.search('<li class=g>.*?<a href="([^"]+?)"[^>]+?>(.+?)</a>.*?<div.*?>(.+?)<br' ,data, re.S)
            if result is not None:
                irch.message(irc, channel, "~U%s~U" % format(result.group(2)), tag='Google')
                irch.message(irc, channel, format(result.group(3)), tag='Google')
                irch.message(irc, channel, "URL: %s" % format(result.group(1)), tag='Google')
            else:
                irch.message(irc, channel, "No search results could be found.", tag='Google')
        except urllib2.HTTPError:
            irch.message(irc, channel, "An error occurred and the search could not be completed.", tag='Google')
    elif command == 'wikipedia' or command == 'wiki':
        if len(args) == 0:
            args = 'Special:Random'
        page = ' '.join(args)
        url = 'http://en.wikipedia.org/wiki/%s' % escapeurl(page.replace(' ','_'))
        try:
            text = load_url(url)
        except urllib2.HTTPError:
            irch.message(irc, channel, '~B%s~B does not exist.' % page, tag='Wikipedia')
            return
        title = re.search('<title>(.+?) - Wikipedia, the free encyclopedia</title>', text).group(1)
        if page.lower() != title.lower():
            redir = title
            url = 'http://en.wikipedia.org/wiki/%s' % escapeurl(redir.replace(' ', '_'))
        else:
            redir = None
        old_text = text
        while '</table>' in old_text and old_text.find('</table>') < old_text.find('<p>'):
            old_text = text
            text = textchannel
        text = old_text
        del old_text
        text = re.sub('(?is)<div class=.+?>.+?</div>', '', text)
        summary = re.search('(?is)<p>([^<>]{0,15}<b>[^<>]+?</b>[^<>]{2,2}.+?)</p>', text)
        if summary is None:
            summary = re.search('(?is)<p>(.+?)</p>', text)
        
        summary = format(re.sub('</?a.*?>', '<u>', summary.group(1)))
        summary = re.sub(r'(?is)\[(?:[0-9]+?|[a-z]+? needed)\]',  '', summary)
        if redir is not None:
            irch.message(irc, channel, "~URedirected to %s~U" % redir, tag='Wikipedia')
        irch.message(irc, channel, '\n'.join(textwrap.wrap(summary, 400)), tag='Wikipedia')
        irch.message(irc, channel, 'Please see %s for more.' % url, tag='Wikipedia')
    elif command == 'define':
        search = ' '.join(args)
        try:
            data = load_url('http://dictionary.reference.com/browse/%s' % escapeurl(search))
        except:
            irch.message(irc, channel, "There was an error loading the entry.")
            return
        matches = re.search('<h2 class="me">(.+?)</h2>.*?<span class="pron">(.+?)</span>.*?<span class="pg">(.+?)</span>.*?<td>(.+?)</td>', data)
        irch.message(irc, channel, '~U~B%s (%s)~B~U' % (matches.group(1), matches.group(3).strip(u'– ,')), tag='Define')
        pron = matches.group(2)
        pron = re.sub('<span class="boldface">(.+?)</span>', r'<b>\1</b>', pron)
        pron = re.sub('<span class="ital-inline">(.+?)</span>', r'<i>\1</i>', pron)
        pron = pron.replace('png', 'gif')
        pron = format(pron)
        irch.message(irc, channel, 'Pronunciation: %s' % pron, tag='Define')
        irch.message(irc, channel, format(matches.group(4).strip()), tag='Define')
    elif command == 'translate':
        string = ' '.join(args)
        try:
            data = load_url('http://ajax.googleapis.com/ajax/services/language/translate?v=1.0&q=%s&langpair=%%7Cen' % escapeurl(string))
        except urllib2.HTTPError:
            irch.message(irc, channel, "Translation failed.")
            return
        logger.debug(data)
        parsed = json.loads(data)
        irch.message(irc, channel, format(parsed['responseData']['translatedText']), tag='Translation')
    elif command == 'spell':
        word = ' '.join(args) # Eh.
        s = aspell.Speller('lang', 'en')
        if s.check(word):
            irch.message(irc, channel, "~B%s~B is spelt correctly. :D" % word)
        else:
            suggestions = s.suggest(word)[:5]
            if not suggestions:
                irch.message(irc, channel, "~B%s~B is spelt incorrectly, and I have not the foggiest clue what you meant. :(" % word)
            else:
                last = suggestions.pop()
                formatted = ', '.join(suggestions)
                if formatted != '':
                    formatted += ' or '
                formatted += last
            irch.message(irc, channel, "~B%s~B is spelt incorrectly. Did you mean one of %s?" % (word, formatted))