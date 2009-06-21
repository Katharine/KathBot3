#!/usr/bin/python

import config
from irc import IRC
import logging

networks = {}

def connect(network):
    networks[network.name] = IRC(network)
    networks[network.name].start()
    logging.info("Started thread for %s." % network)