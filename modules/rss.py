# coding=utf-8
import feedparser
import threading
import time
import networks
import re
import datetime

POLL_INTERVAL = 300

def init():
    feedparser.USER_AGENT = 'KathBot/3'
    add_hook('privmsg', privmsg)
    m('cron').add_cron(POLL_INTERVAL, poll)
    logger.info("Registered cron job every %s seconds." % POLL_INTERVAL)

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if command == 'subscribe':
        if len(args) != 1:
            irc_helpers.message(irc, target, "You must specify a URL to subscribe to.")
            return
        url = args[0]
        feed = feedparser.parse(url)
        if feed.status < 200 or feed.status >= 300:
            irc_helpers.message(irc, target, "No feed found at %s" % url)
            return
        
        if len(feed.entries) == 0:
            irc_helpers.message(irc, target, "The specified feed is empty.")
        
        m('datastore').execute("INSERT INTO rss_subscriptions(network, channel, url) VALUES (?, ?, ?)", irc.network.name, target.lower(), url)
        
        irc_helpers.message(irc, target, "Subscribed %s to %s" % (target, feed.feed.title))

def poll():
    logger.debug("Starting RSS poll.")
    subscriptions = m('datastore').query("SELECT network, channel, url, last_item, etag, last_modified FROM rss_subscriptions")
    for subscription in subscriptions:
        network, channel, url, last_item, etag, last_modified = subscription
        if not network in networks.networks:
            continue
        
        try:
            feed = feedparser.parse(url, etag=etag)
            if feed.get('status', 200) == 304 or len(feed.entries) == 0:
                logger.debug("Received HTTP 304 from %s" % url)
                continue
            if not feed:
                logger.info("Received unexpected blank feed from %s (subscription for %s/%s)" % (url, network, channel))
                continue
            
            latest = feed.entries[0]
            if latest.id == last_item:
                logger.debug("No new items in %s" % url)
                continue
                
            logger.info("New item from %s!" % url)
            
            content = m('irc_helpers').html_to_irc(latest.description)
            if len(content) > 400:
                content = u"%s…" % content[0:397]
            
            irc = networks.networks[network]
            m('irc_helpers').message(irc, channel, u'~U%s – %s~U' % (feed.feed.title, feed.feed.link), tag='RSS')
            m('irc_helpers').message(irc, channel, '~B%s~B' % latest.title, tag='RSS')
            m('irc_helpers').message(irc, channel, content, tag='RSS')
            m('irc_helpers').message(irc, channel, 'More: %s' % latest.link, tag='RSS')
            etag = feed.get('etag', '')
            modified = None
            if 'modified' in feed:
                modified = datetime.datetime(*feed.modified[0:6])
            last_item = latest.guid
            m('datastore').execute('UPDATE rss_subscriptions SET etag = ?, last_modified = ?, last_item = ? WHERE url = ? AND channel = ? AND network = ?', etag, modified, last_item, url, channel, network)
        except Exception, message:
            logger.error("Something went wrong whilst handling the feed %s: %s" % (url, message))
    
    # Wait until we go around again.
    logger.debug("Completed RSS poll.")