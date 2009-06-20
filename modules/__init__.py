import logging

class ModuleAlreadyLoaded(Exception): pass
class ModuleNotLoaded(Exception): pass

hooks = {}
mods = {}

def add_hook(module, hook, function):
    if not hooks.get(hook):
        hooks[hook] = {}
    hooks[hook][module] = function
    logging.info("Added hook %s for module %s" % (hook, module))

def remove_hook(module, hook):
    if hooks.get(hook):
        del hooks[hook][module]

def call_hook(hook, *args, **kwds):
    if hooks.get(hook):
        for module in hooks[hook]:
            try:
                hooks[hook][module](*args, **kwds)
            except Exception, message:
               logging.error("Error calling hook %s on %s: %s" % (hook, module, message))

def get_module(module):
    return modules.get(module)

def load_module(module):
    if mods.get(module):
        raise ModuleAlreadyLoaded, module
    
    mods[module] = __import__(module, globals(), locals(), [], -1)
    mods[module].add_hook = lambda hook, function: add_hook(module, hook, function)
    mods[module].remove_hook = lambda hook: remove_hook(module, hook)
    mods[module].m = lambda module: get_module(module)
    mods[module].init()
    logging.info("Loaded module %s", module)
    
def unload_module(module):
    if not mods.get(module):
        raise ModuleNotLoaded, module
    for hook in hooks:
        if hooks[hook].get(module):
            del hooks[hook][module]
    
    del mods[module]