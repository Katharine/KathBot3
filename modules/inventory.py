#Davy//8-1-09
import random

interactions = ['hug', 'kis', 'lic', 'cud', 'nuz', 'pet', 'snu', 'lov']
actions = ['trashes', 'deletes', 'drops', 'removes', 'throws', 'gives', 'hands', 'tosses', 'explodes', 'looks', 'examines', 'inspects']
give_words = ['throws', 'gives', 'hands', 'tosses']
trash_words = ['trashes', 'deletes', 'drops', 'removes']
examine_words = ['examines', 'inspects', 'looks']
destruct_words = ['explodes']

def parse_actions(irc, channel, user, message):
    irch = m('irc_helpers')
    words, pattern = make_pattern(irc, channel, user, message)
    length = len(pattern)
    if pattern[0:4] == ['action', 'amount', 'item', 'nick'] and length >= 4:
        if words[0] not in give_words:
            return
        #/me gives amount item to nick
        #
        target = words[3]
        amount = words[1]
        item = words[2]
        irch.message(irc, channel, '(%s lost %s %s)' % (user.nick, amount, item))
        irch.message(irc, channel, '(%s acquired %s %s)' % (target.nick, amount, item))
        revoke_item(user.uid, item_id_by_name(item), amount)
        give_item(target.uid, item_id_by_name(item), amount)
    elif pattern[0:4] == ['action', 'nick', 'amount', 'item'] and length >= 4:
        if words[0] not in give_words:
            return
        #/me gives nick amount item
        #
        target = words[1]
        amount = words[2]
        item = words[3]
        irch.message(irc, channel, '(%s lost %s %s)' % (user.nick, amount, item))
        irch.message(irc, channel, '(%s acquired %s %s)' % (target.nick, amount, item))
        revoke_item(user.uid, item_id_by_name(item), amount)
        give_item(target.uid, item_id_by_name(item), amount)
    elif pattern[0:3] == ['action', 'item', 'nick'] and length >= 3:
        if words[0] not in give_words:
            return
        #/me gives an item to nick
        #
        target = words[2]
        item = words[1]
        irch.message(irc, channel, '(%s lost one %s)' % (user.nick, item))
        irch.message(irc, channel, '(%s acquired one %s)' % (target.nick, item))
        revoke_item(user.uid, item_id_by_name(item), 1)
        give_item(target.uid, item_id_by_name(item), 1)
    elif pattern[0:3] == ['action', 'nick', 'item'] and length >= 3:
        if words[0] not in give_words:
            return
        #/me gives nick an item
        #
        target = words[1]
        item = words[2]
        irch.message(irc, channel, '(%s lost one %s)' % (user.nick, item))
        irch.message(irc, channel, '(%s acquired one %s)' % (target.nick, item))
        revoke_item(user.uid, item_id_by_name(item), 1)
        give_item(target.uid, item_id_by_name(item), 1)
    elif pattern[0:3] == ['action', 'nick', 'interaction'] and length >= 3:
        if words[0] not in give_words:
            return
        #/me gives nick a hug
        #
        target = words[1]
        interaction = words[2]
        give_stat(target.uid, stat_id_by_name(interaction))
        irch.message(irc, channel, '(%s has been %s)' % (target.nick, get_stat_fullname(stat_id_by_name(interaction))))
    elif pattern[0:2] == ['interaction', 'nick'] and length >= 2:
        #/me hugs nick
        #
        target = words[1]
        interaction = words[0]
        give_stat(target.uid, stat_id_by_name(interaction))
        irch.message(irc, channel, '(%s has been %s)' % (target.nick, get_stat_fullname(stat_id_by_name(interaction))))
    elif pattern[0:3] == ['action', 'amount', 'item'] and length >= 3:
        if words[0] in trash_words:
            #/me drops amount item
            #
            action = words[0]
            amount = words[1]
            item = words[2]
            irch.message(irc, channel, '(%s lost %s %s)' % (user.nick, amount, item))
            revoke_item(user.uid, item_id_by_name(item), amount)
        elif words[0] in destruct_words:
            #/me explodes amount item
            #
            action = words[0]
            amount = words[1]
            item = words[2]
            irch.message(irc, channel, '(%s lost %s %s, but gained some ashes)' % (user.nick, amount, item))
            revoke_item(user.uid, item_id_by_name(item), amount)
            give_item(user.uid, item_id_by_name('Ashes'), amount)
    elif pattern[0:2] == ['action', 'item'] and length >= 2:
        if words[0] in trash_words:
            #/me drops an item
            #
            action = words[0]
            item = words[1]
            irch.message(irc, channel, '(%s lost one %s)' % (user.nick, item))
            revoke_item(user.uid, item_id_by_name(item), 1)
        elif words[0] in destruct_words:
            #/me explodes her item
            #
            action = words[0]
            item = words[1]
            irch.message(irc, channel, '(%s lost one %s, but gained some ashes)' % (user.nick, item))
            revoke_item(user.uid, item_id_by_name(item), 1)
            give_item(user.uid, item_id_by_name('Ashes'), 1)
        elif words[0] in examine_words:
            #/me looks at item
            item = words[1]
            description = get_item_description(item_id_by_name(item))
            if description != '' and description != None:
                irch.message(irc, channel, "~B(Examining '%s')~B %s" % (item, description))
            else:
                irch.message(irc, channel, "(You don't have one of those to examine)")

###
def make_pattern(irc, channel, user, message):
    temp = message.split(' ')
    words = []
    pattern = []
    index = 0
    for word in temp:
        if item_exists(word) and user_has_item(user.uid, word):
            pattern.append('item')
            words.append(word)
        #Yucky hopefully-temporary hack to slice s's off words to *try* and lazily find plurals.
        if item_exists(word[0:len(word)-1]) and user_has_item(user.uid, word[0:len(word)-1]):
            pattern.append('item')
            words.append(word)
        if word in actions:
            pattern.append('action')
            words.append(word)
        if word[0:3] in interactions:
            pattern.append('interaction')
            words.append(word[0:3])
        if nick_is_present(irc, channel, word):
            pattern.append('nick')
            words.append(make_user(irc, word))
        try:
            if item_exists(word + " " + temp[index+1]):
                pattern.append('item')
                words.append(word + " " + temp[index+1])
        except:
            try:
                if int(word) > 0:
                    pattern.append('amount')
                    words.append(word)
            except:
                index += 1
                continue
        index += 1
    return words, pattern

###
def make_user(irc, nick):
    user = m('chantrack').create_user(irc, nick)
    user.uid = m('security').get_user_id(user)
    return user

def nick_is_present(irc, channel, nick):
    channels = m('chantrack').nick_channels(irc, nick)
    if channel in channels:
        return True
    return False

###
def item_exists(query):
    temp = m('datastore').query('SELECT name FROM inventory_items')
    items = []
    for item in temp:
        if item[0].strip() != '' and item[0].strip() != None:
            items.append(item[0].strip().lower())
    if query.lower() in items:
        return True
    return False

###
def give_item(userid, itemid, count, amount):
    count = m('datastore').query('SELECT count FROM inventory_user_items WHERE userid = ? AND itemid = ?', userid, itemid)
    if len(count) == 0:
        m('datastore').execute('INSERT INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, itemid, amount)
    else:
        m('datastore').execute("UPDATE inventory_user_items SET count = ? WHERE userid = ? AND itemid = ?", count[0][0] + amount, userid, itemid)

###
def sudo_give_item(userid, itemid, amount):
    count = m('datastore').query('SELECT count FROM inventory_user_items WHERE userid = ? AND itemid = ?', userid, itemid)
    if len(count) == 0:
        m('datastore').execute('INSERT INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, itemid, amount)
    else:
        m('datastore').execute("UPDATE inventory_user_items SET count = ? WHERE userid = ? AND itemid = ?", count[0][0] + amount, userid, itemid)

###       
def revoke_item(userid, itemid, amount):
    count = m('datastore').query('SELECT count FROM inventory_user_items WHERE userid = ? AND itemid = ?', userid, itemid)
    if len(count) == 0:
        #Uh..They don't have the item. >.>
        return #Return and do nothing, though we should never get here.
    elif count[0][0] - amount <= 0:
        m('datastore').execute('DELETE FROM inventory_user_items WHERE userid = ? AND itemid = ?', userid, itemid)
    else:
        m('datastore').execute("UPDATE inventory_user_items SET count = ? WHERE userid = ? AND itemid = ?", count[0][0] - amount, userid, itemid)

def give_stat(userid, itemid):
    
    count = m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, itemid)
    if len(count) == 0:
        m('datastore').execute('INSERT INTO inventory_user_stats (userid, itemid, count) VALUES (?, ?, ?)', userid, itemid, 1)
    else:
        m('datastore').execute("UPDATE inventory_user_stats SET count = ? WHERE userid = ? AND itemid = ?", count[0][0] + 1, userid, itemid)

###
def add_item(name, description, effects):
    if len(m('datastore').query('SELECT description FROM inventory_items WHERE name = ?', name)) == 0:
        m('datastore').execute('REPLACE INTO inventory_items (name, description, effects) VALUES (?, ?, ?)', name, description, effects)
    else:
        m('datastore').execute('UPDATE inventory_items SET description = ?, effects = ? WHERE name = ?', description, effects, name)
    return True

###
def add_effect(name, description):
    if len(m('datastore').query('REPLACE description FROM inventory_effects WHERE name = ?', name)) == 0:
        m('datastore').execute('INSERT INTO inventory_effects (name, description) VALUES (?, ?)', name, description)
    else:
        m('datastore').execute('UPDATE inventory_effects SET description = ? WHERE name = ?', description, name)
    return True

###
def add_stat(shortname, fullname, description):
    if len(m('datastore').query('SELECT shortname FROM inventory_stats WHERE shortname = ?', shortname)) == 0:
        m('datastore').execute('INSERT INTO inventory_stats (shortname, fullname, description) VALUES (?, ?, ?)', shortname, fullname, description)
    else:
        m('datastore').execute('UPDATE inventory_stats SET fullname = ?, description = ? WHERE shortname = ?', fullname, description, shortname)
    return True

###
def user_has_effect(userid, effectquery):
    data = m('datastore').query('SELECT itemid FROM inventory_user_items WHERE userid = ?', userid)
    effects = []
    for item in data:
        effects.extend(m('datastore').query('SELECT effects FROM inventory_items WHERE userid = ? AND id = ?', userid, item[0]).split(','))
    if effectquery in effects:
        return True
    return False

###     
def user_has_item(userid, itemquery):
    itemquery = itemquery.lower()
    data = m('datastore').query('SELECT itemid FROM inventory_user_items WHERE userid = ?', userid)
    
    items = []
    for item in data:
        items.append(item[0])
        
    itemnames = []
    for item in items:
            itemnames.append(item_name_by_id(item).lower())
                
    if itemquery in itemnames:
        return True
    return False

###     
def return_user_stat(userid, statquery):
    data = m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND name = ?', userid, statquery)
    items = []
    for item in data:
        items.extend(item[0])
    if itemquery in items:
        return True
    return False

###
def item_id_by_name(name):
    ID = m('datastore').query('SELECT id FROM inventory_items WHERE name = ?', name)
    if len(ID) <= 0:
        return ''
    return ID[0][0]

###
def item_name_by_id(ID):
    name = m('datastore').query('SELECT name FROM inventory_items WHERE id = ?', ID)
    if len(name) <= 0:
        return ''
    return name[0][0]

###
def effect_id_by_name(name):
    ID = m('datastore').query('SELECT id FROM inventory_effects WHERE name = ?', name)
    if len(ID) <= 0:
        return ''
    return ID[0][0]

###
def effect_name_by_id(ID):
    name = m('datastore').query('SELECT name FROM inventory_effects WHERE id = ?', ID)
    if len(name) <= 0:
        return ''
    return name[0][0]

###
def stat_id_by_name(shortname):
    ID = m('datastore').query('SELECT id FROM inventory_stats WHERE shortname = ?', shortname)
    if len(ID) <= 0:
        return ''
    return ID[0][0]

###
def stat_name_by_id(ID):
    shortname = m('datastore').query('SELECT shortname FROM inventory_stats WHERE id = ?', ID)
    if len(shortname) <= 0:
        return ''
    return shortname[0][0]

###
def get_item_description(ID):
    description = m('datastore').query('SELECT description FROM inventory_items WHERE id = ?', ID)
    if len(description) <= 0:
        return ''
    return description[0][0]

###
def get_effect_description(ID):
    description = m('datastore').query('SELECT description FROM inventory_effects WHERE id = ?', ID)
    if len(description) <= 0:
        return ''
    return description[0][0]
    
###
def get_stat_fullname(ID):
    description = m('datastore').query('SELECT fullname FROM inventory_stats WHERE id = ?', ID)
    if len(description) <= 0:
        return ''
    return description[0][0]

###
def list_inventory(userid):
    ids = m('datastore').query('SELECT itemid FROM inventory_user_items WHERE userid = ?', userid)
    counts = m('datastore').query('SELECT count FROM inventory_user_items WHERE userid = ?', userid)
    inventory = {}
    index = 0
    while index < len(ids):
        inventory[item_name_by_id(ids[index][0])] = counts[index][0]
        index += 1
    return inventory;

###
def list_stats(userid):
    ids = m('datastore').query('SELECT itemid FROM inventory_user_stats WHERE userid = ?', userid)
    counts = m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ?', userid)
    stats = {}
    index = 0
    while index < len(ids):
        stats[get_stat_fullname(ids[index][0])] = counts[index][0]
        index += 1
    return stats;

###
def create_user_maybe(userid):
    #~Add user if they don't exist BEFORE interacting!~#
    if len(m('datastore').query('SELECT count FROM inventory_user_stats WHERE userid = ? AND itemid = ?', userid, stat_id_by_name('ALIVE'))) == 0:
        m('datastore').execute('INSERT INTO inventory_user_items (userid, itemid, count) VALUES (?, ?, ?)', userid, item_id_by_name('Fork'), 1)
        m('datastore').execute('INSERT INTO inventory_user_stats (userid, itemid, count) VALUES (?, ?, ?)', userid, stat_id_by_name('ALIVE'), 1)

######################
######################
def init():
    add_hook('message', message)
    add_hook('privmsg', privmsg)

COMMANDS = frozenset(('inventory', 'inspect', 'examine', 'give', 'sudogive', 'trash', 'delete', 'addeffect', 'additem', 'addstat'))

def message(irc, channel, origin, command, args):
    irch = m('irc_helpers')
    if command not in COMMANDS:
        return
    userid = m('security').get_user_id(origin)
    if userid == None:
        return #Only people with #KathBot3 accounts can use this module.
        irch.message(irc, channel, "You can not use the inventory module to unless you have a KB3-account.")
    
    create_user_maybe(userid)
    
    if command == 'inventory':
        itemlist = list_inventory(userid)
        istring = '%s has ' % m('security').get_canonical_nick(origin.nick)
        for item in itemlist:
            istring += '%s %s, ' % (itemlist[item], item)
        if len(itemlist) <= 0:
            istring += 'no items'
        statlist = list_stats(userid)
        if len(statlist) == 1:
            istring += "and doesn't currenly have any statistics, but is noted to be alive."
        else:
            istring += 'has been '
            for stat in statlist:
                if stat == 'Alive':
                    continue
                istring += '%s %s times, ' % (stat, statlist[stat])
            istring = istring[0:len(istring)-2]
            istring += ', and is noted to be alive.'
        irch.message(irc, channel, istring)
    elif command == 'inspect' or command == 'examine':
        #!examine item   -or-   !inspect item
        if len(args) >= 1:
            name = ' '.join(args).strip()
            description = get_item_description(item_id_by_name(name))
            if description != '' and description != None:
                irch.message(irc, channel, "~B(Examining '%s')~B %s" % (name, description))
            else:
                irch.message(irc, channel, "You don't have one of those to examine.")
    elif command == "give":
        #!give nick amount item
        if len(args) == 2:
            item = args[1]
            target = args[0]
            target = make_user(irc, target)
            if not nick_is_present(irc, channel, target.nick):
                return #Can't give to someone who isn't here.
            if not user_has_item(userid, item_id_by_name(item)):
                irch.message(irc, channel, "You can not give away something you don't have.")
                return
            irch.message(irc, channel, '[%s lost one %s.]' % (origin.nick, item))
            irch.message(irc, channel, '[%s acquired one %s.]' % (target.nick, item))
            revoke_item(userid, item_id_by_name(item))
            give_item(target.uid, item_id_by_name(item), 1)
        elif len(args) == 3:
            item = args[2]
            amount = args[1]
            target = args[0]
            target = make_user(irc, target)
            if not nick_is_present(irc, channel, target.nick):
                return #Can't give to someone who isn't here.
            if not user_has_item(userid, item_id_by_name(item)):
                irch.message(irc, channel, "You can not give away something you don't have.")
                return
            irch.message(irc, channel, '[%s lost %s %s.]' % (origin.nick, amount, item))
            irch.message(irc, channel, '[%s acquired %s %s.]' % (target.nick, amount, item))
            revoke_item(userid, item_id_by_name(item), amount)
            give_item(target.uid, item_id_by_name(item), amount)
    elif command == 'sudogive':
        #!sudogive nick amount item
        if len(args) == 2:
            target = make_user(irc, args[0])
            item = item_id_by_name(' '.join(args[1:]))
            if not item_exists(item_name_by_id(item)):
                return
            sudo_give_item(target.uid, item, 1)
            irch.message(irc, channel, '[%s acquired one %s.]' % (target.nick, item_name_by_id(item)))
        elif len(args) == 3:
            target = make_user(irc, args[0])
            item = item_id_by_name(' '.join(args[2:]))
            amount = args[1]
            if not item_exists(item_name_by_id(item)):
                return
            sudo_give_item(target.uid, item, amount)
            irch.message(irc, channel, '[%s acquired %s %s.]' % (target.nick, amount, item_name_by_id(item)))
    elif command == 'trash' or command == 'delete':
        #!trash amount item   -or-   !delete amount item
        if len(args) == 2:
            item = args[1]
            amount = args[0]
            irch.message(irc, channel, '[%s lost one %s.]' % (origin.nick, item))
            revoke_item(userid, item_id_by_name(item), 1)
        elif len(args) == 1:
            item = args[0]
            irch.message(irc, channel, '[%s lost %s %s.]' % (origin.nick, amount, item))
            revoke_item(userid, item_id_by_name(item), 1)
    elif command == 'addeffect':
        args = ' '.join(args)
        if args.find('{') and args.find('}'):
            #!addeffect name (description)
            name = args[0:args.find('{')]
            description = args[args.find('{')+1:args.find('}')]
            add_effect(name, description)
            irch.message(irc, channel, "Effect Added.")
        else:
            irch.message(irc, channel, "Invalid Syntax.")
    elif command == 'addstat':
        args = ' '.join(args)
        if args.find('{') and args.find('}'):
            #!addstat name (description)
            name = args[0:args.find('{') - 1]
            description = args[args.find('{')+1:args.find('}')]
            add_stat(name[0:3].lower(), name, description)
            irch.message(irc, channel, "Stat ~B%s~B added." % name)
        else:
            irch.message(irc, channel, "Invalid Syntax.")
    elif command == 'additem':
        args = ' '.join(args)
        if args.find('{') and args.find('}') and args.find(','):
            #!additem name (description) with (effect1, effect2, effect3, etc..)
            name = args[0:args.find('{')].strip()
            description = args[args.find('{')+1:args.find('}')]
            temp = args[args.find('with (')+6:len(args)-1].split(',')
            effects = []
            for effect in temp:
                if effect.strip() != '' and effect.strip() != None:
                    effects.append(effect.strip())
            effects = ','.join(effects)
            add_item(name, description, effects)
            logger.info('Name: "%s" Desc: "%s" Effects: "%s"' % (name, description, effects))
            irch.message(irc, channel, "Item Added.")
        else:
            irch.message(irc, channel, "Invalid Syntax.")


def privmsg(irc, origin, args):
    irch = m('irc_helpers')
    message = args[1]
    channel = args[0]
    userid = m('security').get_user_id(origin)
    if args == None:
        return
    if userid == None:
        return #Only people with #KathBot3 accounts can use this module.
    if '\x01ACTION' not in message:
        return
    
    create_user_maybe(userid)
    #~#
    origin.nick = m('security').get_canonical_nick(origin.nick)
    origin.uid = userid
    message = message[7:len(message)-1]
    parse_actions(irc, channel, origin, message)
