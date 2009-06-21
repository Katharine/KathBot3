#!/usr/bin/python

import config
from irc import IRC
import modules
import logging

networks = {}

def main():
    for module in config.modules:
        modules.load_module(module)
    
    for name in config.networks:
        network = config.networks[name]
        networks[name] = IRC(network)
        networks[name].start()
        logging.info("Started thread for %s" % name)

if __name__ == '__main__':
    main()