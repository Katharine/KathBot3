import logging
import sys

class ModuleAlreadyLoaded(Exception): pass
class ModuleNotLoaded(ImportError): pass

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
        try:
            for module in hooks[hook]:
                try:
                    hooks[hook][module](*args, **kwds)
                except Exception, message:
                   logging.error("Error calling hook %s on %s: %s" % (hook, module, message))
        except RuntimeError, message:
            logging.warn("Aborted hook %s due to looping failure: %s" % (hook, message))

def get_module(module_name):
    module = mods.get(module_name)
    if not module:
        raise ModuleNotLoaded, "%s is not loaded." % module_name
    
    return module

def load_module(module):
    if mods.get(module):
        raise ModuleAlreadyLoaded, "%s is already loaded." % module
    
    mods[module] = __import__(module, globals(), locals(), [], -1)
    mods[module].add_hook = lambda hook, function: add_hook(module, hook, function)
    mods[module].remove_hook = lambda hook: remove_hook(module, hook)
    mods[module].m = lambda module: get_module(module)
    try:
        init_module = getattr(mods[module], 'init')
    except AttributeError:
        pass
    else:
        init_module()
    logging.info("Loaded module %s", module)
    
def unload_module(module):
    if not mods.get(module):
        raise ModuleNotLoaded, "%s is not loaded." % module
    for hook in hooks:
        if hooks[hook].get(module):
            del hooks[hook][module]
    
    try:
        modules[module].shutdown()
    except:
        pass
    
    del mods[module]
    del sys.modules['modules.%s' % module]