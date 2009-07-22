#!/usr/bin/python

import config
import modules
import networks
import logging

def main():
    import locale
    locale.setlocale(locale.LC_NUMERIC, '')
    
    for module in config.modules:
        modules.load_module(module)
    
    for name in config.networks:
        network = config.networks[name]
        networks.connect(network)
    
    logging.info("Ready.")

if __name__ == '__main__':
    main()