def add_tags():
    m('dynamic').add_tag("webget", tag_webget, True)
    m('dynamic').add_tag("webescape", tag_webescape, True)

def init():
    add_hook('loaded', evt_loaded)
    add_tags()

def evt_loaded(mod):
    if mod == 'dynamic':
        add_tags()

def tag_webget(node, context):
    uri = m('dynamic').treelevel(node, context)
    
    body = m('reference').load_url(uri)
    return body

def tag_webescape(node, context):
    return m('reference').escapeurl(m('dynamic').treelevel(node, context))
