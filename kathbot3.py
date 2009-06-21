#!/usr/bin/python

import config
import modules
import networks

def main():
    for module in config.modules:
        modules.load_module(module)
    
    for name in config.networks:
        network = config.networks[name]
        networks.connect(network)

if __name__ == '__main__':
    main()