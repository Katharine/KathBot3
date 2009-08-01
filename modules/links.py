# encoding=utf-8
#
#Davy//16-7-09
#
import urllib2
import re

cmdtag = '~B[links]~B'
reg_a = '(?i)<a.*?href.*?="(.+?)".*?>'
reg_embed = '(?i)<embed.*?src.*?="(.+?)".*?>'
reg_img = '(?i)<img.*?src.*?=.*?"(.+?)".*?>'

def makelinks(urls):
    links = []
    if urls != None:
        if len(urls) > 0:
            for url in urls:
                links.append(url.strip())
    return links

def init():
    add_hook('message', message)

def message(irc, channel, origin, command, args):
    irc_helpers = m('irc_helpers')
    target = channel
    if command == 'links':
        if len(args) > 0 and len(args) <= 2:
            url = args[0]
            try:
                handle = urllib2.urlopen(url)
                data = handle.read()
                handle.close()
            except urllib2.HTTPError, error:
                irc_helpers.message(irc, target,'Error opening URL: ~B%s~B' % error)
                return
            a= makelinks(re.findall(reg_a, data))
            embed = makelinks(re.findall(reg_embed, data))
            img = makelinks(re.findall(reg_img, data))
            
            acount = len(a)
            embedcount = len(embed)
            imgcount = len(img)
            all = []
            all.extend(a)
            all.extend(embed)
            all.extend(img)
            tcount = len(all)
            nd = []
            for link in all:
                if link not in nd:
                    nd.append(link)
            ndcount = len(nd)
            
            irc_helpers.message(irc, target,'%s Scanned %s for hyperlinks and urls. (%s total links found, %s without duplicates.)' % (cmdtag, url, tcount, ndcount))
            irc_helpers.message(irc, target,'%s ~B%s~B from ~B<a>~B tags;' % (cmdtag, acount))
            irc_helpers.message(irc, target,'%s ~B%s~B from ~B<embed>~B tags;' % (cmdtag, embedcount))
            irc_helpers.message(irc, target,'%s ~B%s~B from ~B<img>~B tags;' % (cmdtag, imgcount))
            
            if len(args) == 2:
                search = args[1]
                matches = []
                for link in nd:
                    if link not in matches:
                        if link.find(search) != -1:
                            matches.append(link)
                if len(matches) > 0:
                    irc_helpers.message(irc,target,'%s You supplied the search term ~B"%s"~B, which matched ~B%s~B links:' % (cmdtag, search, len(matches)))
                    maxindex = 5
                    index = 0
                    while index < maxindex and index < len(matches):
                        irc_helpers.message(irc,target,'%s ~B%s~B' % (cmdtag, matches[index]))
                        index += 1
                    if index < len(matches):
                        irc_helpers.message(irc,target,'%s ~B(Output capped at 7 results)~B' % cmdtag)
                else:
                    irc_helpers.message(irc,target,'%s You supplied the search term ~B"%s"~B, but it did not match any links.' % (cmdtag, search))
                    irc_helpers.message(irc,target,'~B||~B'.join(nd))
                            
        else:
            irc_helpers.message(irc,target,'Please supply one URL to scan for links.')
        
		