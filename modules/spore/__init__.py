# "import Spore" is effectively executed automatically by the module loader.
import networks

SPORE_TYPES = {
    'VEHICLE': 'moving thingy',
    'UFO': 'space thingy',
    'BUILDING': 'building thingy',
    'CREATURE': 'living thingy',
}

def init():
    add_hook('message', message)
    if 'spore_users' not in m('datastore').general:
        m('datastore').general['spore_users'] = {}
    m('cron').add_cron(600, check_stuff)

def message(irc, channel, origin, command, args):
    if command == 'achievements':
        if len(args) == 1:
            user = args[0]
            achievements = Spore.GetAchievementsForUser(user, 0, 100)
            names = ', '.join([x.mName for x in achievements])
            m('irc_helpers').message(irc, channel, "Achievements for ~B%s~B: %s" % (user, names), 'Spore')
        elif len(args) == 2:
            user1 = args[0]
            user2 = args[1]
            ach1 = set([x.mName for x in Spore.GetAchievementsForUser(user1, 0, 100)])
            ach2 = set([x.mName for x in Spore.GetAchievementsForUser(user2, 0, 100)])
            common = ach1 & ach2
            user1only = ach1 - ach2
            user2only = ach2 - ach1
            m('irc_helpers').message(irc, channel, "~UComparing ~B%s~B and ~B%s~B~U" % (user1, user2), tag='Spore')
            m('irc_helpers').message(irc, channel, "Only ~B%s~B has: %s" % (user1, ', '.join(user1only)), tag='Spore')
            m('irc_helpers').message(irc, channel, "Only ~B%s~B has: %s" % (user2, ', '.join(user2only)), tag='Spore')
            m('irc_helpers').message(irc, channel, "Both ~B%s~B and ~B%s~B have: %s" % (user1, user2, ', '.join(common)), tag='Spore')
    elif command == 'myspore':
        uid = m('security').get_user_id(origin)
        if uid is None:
            m('irc_helpers').message(irc, channel, "You must have a %s account for that to work!" % irc.nick)
            return
        else:
            data = m('datastore').general['spore_users']
            data[uid] = args[0]
            m('datastore').general['spore_users'] = data
            m('datastore').users[uid]['spore_achievements'] = set([x.mId for x in Spore.GetAchievementsForUser(args[0], 0, 100)])
            m('irc_helpers').message(irc, channel, "Tracking spore stuff for ~B%s~B (~B%s~B achievements so far)." % (args[0], len(m('datastore').users[uid]['spore_achievements'])))
    elif command == 'sporespam':
        if args[0] == 'on':
            m('datastore').channels[(irc, channel)]['spore_enabled'] = True
            m('irc_helpers').message(irc, channel, "Enabled Spore-related spam in ~B%s~B." % channel)
        else:
            del m('datastore').channels[(irc, channel)]['spore_enabled']
            m('irc_helpers').message(irc, channel, "Disabled Spore-related spam in ~B%s~B." % channel)
            
def announce(uid, message):    
    for network in networks.networks:
        irc = networks.networks[network]
        channels = m('chantrack').uid_channels(irc, uid)
        for channel in channels:
            if 'spore_enabled' in m('datastore').channels[(irc, channel)]:
                m('irc_helpers').message(irc, channel, message % {'nick': channels[channel]}, tag='Spore')

def check_stuff():
    users = m('datastore').general['spore_users']
    for uid in users:
        spore_name = users[uid]
        current = m('datastore').users[uid]['spore_achievements']
        logger.debug("Doing %s. %s achievements." % (uid, len(current)))
        achievements = Spore.GetAchievementsForUser(spore_name, 0, 100)
        ach_ids = set([x.mId for x in achievements])
        difference = ach_ids - current
        for achievement in achievements:
            if achievement.mId not in difference:
                continue
            # Announce!
            announce(uid, '~B%%(nick)s~B has achieved ~B%s~B: %s' % (achievement.mName, achievement.mText))
        m('datastore').users[uid]['spore_achievements'] = ach_ids
        
        creations = Spore.GetAssetDataForUser(spore_name, limit=10)
        if not creations:
            continue
        if 'spore_last_creation' not in m('datastore').users[uid]:
            m('datastore').users[uid]['spore_last_creation'] = creations[0].aid
            continue
        
        last_known_creation = m('datastore').users[uid]['spore_last_creation']
        already_done = set()
        for creation in creations:
            if creation.name in already_done:
                continue
            if creation.aid <= last_known_creation:
                break
            already_done.add(creation.name)
            if creation.parent is None:
                announce(uid, '~B%%(nick)s~B just made ~B%s~B, a new ~B%s~B!' % (creation.name, SPORE_TYPES[creation.atype]))
            else:
                announce(uid, '~B%%(nick)s~B evolved ~B%s~B, a ~B%s~B!' % (creation.name, SPORE_TYPES[creation.atype]))
        m('datastore').users[uid]['spore_last_creation'] = creations[0].aid
