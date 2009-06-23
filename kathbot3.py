#!/usr/bin/python

import config
import modules
import networks
import logging

def main():
    for module in config.modules:
        modules.load_module(module)
    
    for name in config.networks:
        network = config.networks[name]
        networks.connect(network)
    
    logging.info("Ready.")

if __name__ == '__main__':
    main()