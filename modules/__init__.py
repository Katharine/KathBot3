import sys
import logging
import traceback
import threading
import os

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
        RunHook(hook, *args, **kwds)

class RunHook(threading.Thread):
    def __init__(self, hook, *args, **kwds):
        threading.Thread.__init__(self, name=hook)
        self.hook = hook
        self.args = args
        self.kwds = kwds
        self.start()
    
    def run(self):
        try:
            for module in hooks[self.hook]:
                try:
                    hooks[self.hook][module](*self.args, **self.kwds)
                except Exception, message:
                   logging.error("Error calling hook %s on %s: %s" % (self.hook, module, traceback.format_exc()))
        except RuntimeError, message:
            logging.warn("Aborted hook %s due to looping failure: %s" % (self.hook, message))

def get_module(module_name):
    if module_name not in mods:
        raise ModuleNotLoaded, "%s is not loaded." % module_name
    
    return mods[module_name]

def load_module(module):
    if mods.get(module):
        raise ModuleAlreadyLoaded, "%s is already loaded." % module
    
    mods[module] = __import__(module, globals(), locals(), [], -1)
    mods[module].add_hook = lambda hook, function: add_hook(module, hook, function)
    mods[module].remove_hook = lambda hook: remove_hook(module, hook)
    mods[module].m = lambda module: get_module(module)
    mods[module].ModuleNotLoaded = ModuleNotLoaded
    mods[module].logger = logging.getLogger(module)
    
    # Woo, modules with dependencies.
    if os.path.isdir('modules/%s' % module):
        files = os.listdir('modules/%s' % module)
        for filename in files:
            if filename.endswith('.py') and filename != '__init__.py':
                logging.info("Importing submodule %s.%s" % (module, filename[:-3]))
                setattr(mods[module], filename[:-3], getattr(__import__('%s.%s' % (module, filename[:-3]), globals(), locals(), [], -1), filename[:-3]))
    
    try:
        init_module = getattr(mods[module], 'init')
    except AttributeError:
        pass
    else:
        init_module()
    
    call_hook('loaded', module)
    logging.info("Loaded module %s", module)
    
def unload_module(module):
    if not mods.get(module):
        raise ModuleNotLoaded, "%s is not loaded." % module
    for hook in hooks:
        if hooks[hook].get(module):
            del hooks[hook][module]
    
    try:
        mods[module].shutdown()
    except:
        pass
    
    del mods[module]
    del sys.modules['modules.%s' % module]
    
    # Woo, modules with dependencies.
    if os.path.isdir('modules/%s' % module):
        files = os.listdir('modules/%s' % module)
        for filename in files:
            if filename.endswith('.py') and filename != '__init__.py':
                logging.info("Unimporting submodule %s.%s" % (module, filename[:-3]))
                del sys.modules['modules.%s.%s' % (module, filename[:-3])]
    
    call_hook('unloaded', module)