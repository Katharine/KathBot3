# encoding=utf-8
#
#Davy//16-7-09
#

import threading
import time

class VoteQuery(threading.Thread):
    def __init__(self, thread_id, irc, target):
        self.irc = irc
        self.target = target
        self.thread_id = thread_id
        self.query = ""
        self.voted = {}
        self.length = 30 #Length in time the vote lasts before it is closed.
        self.elapsed = 0
        self.options = {}
        self.running = False
        self.reminded = False
        self.used = False #We have to make sure __init__ runs if this thread has already been used. Since we don't delete old class instances(old thread definitions), we need a way to make sure threads that have already been used get all their variables reset. Therefore... self.used is set to True when the thread closes itself after finishing a vote.#
        self.starttime = time.time()
        self.curtime = time.time()
        threading.Thread.__init__(self, name=thread_id)
    
    def run(self):
        logger.info("Starting 'VoteQuery' thread for %s." % self.thread_id)
        self.running = True
        
        #The vote is currently going on
        while self.running:
            self.curtime = time.time()
            self.elapsed = self.curtime - self.starttime
            if self.elapsed >= self.length/2 and self.reminded == False:
                m('irc_helpers').message(self.irc,self.target,'%s There is about ~B%s seconds~B left for the current vote! (Type ~B"!vote"~B to view to redisplay the query.)' % (cmdtag, int(round(self.length/2))))
                self.reminded = True
            if self.elapsed <= self.length:
                time.sleep(1)
            else:
                self.scores = {}
                self.scorelist = []
                self.ties = {}
                
                #~Below is the type of code I'll never remember unless I explain it. Basically, for every option, check if the option's score is in the dictionary of scores. If it isn't, add it. But if it is, it means that another option has the same score, and this amounts to a tie. Therefore, add the option's name to the dictionary of ties, and also add the option that had the same score as the one that we just tested. For every option, no matter what, add its score to the list 'scorelist', and then later we will sort it in ascending order and use the last value to determine the winning (or possibly tieing) score. (Phew.)--Added omission of zeros from ties.
                for option in self.options:
                    if self.options[option][1] in self.scores and self.options[option][1] != 0:
                        self.ties[self.options[option][0]] = self.options[option][1]
                        self.ties[self.scores[self.options[option][1]]] = self.options[option][1]
                    else:
                        self.scores[self.options[option][1]] = self.options[option][0]
                    self.scorelist.append(self.options[option][1])
                self.scorelist.sort()
                #~End of completely confusing code.
                
                self.winner = 0
                if len(self.ties) == 0:
                    self.winner = self.scorelist[len(self.scorelist)-1]
                    m('irc_helpers').message(self.irc,self.target,'%s The current query on ~B"%s"~B is closed, and ~B"%s"~B won with ~B%s~B votes.' % (cmdtag, self.query, self.scores[self.winner], self.winner))
                    self.running = False
                    self.used = True
                    logger.info("Terminating 'VoteQuery' thread for %s." % self.thread_id)
                    return
                else:
                    self.vnum = 0
                    self.vlist = []
                    for option in self.ties:
                        self.vnum = self.ties[option]
                        self.vlist.append(option)
                    m('irc_helpers').message(self.irc,self.target,'%s The current query on ~B"%s"~B is closed, and there was a tie of ~B%s~B votes between ~B%s~B.' % (cmdtag, self.query, self.vnum, ", ".join(self.vlist)))
                    self.running = False
                    self.used = True
                    logger.info("Terminating 'VoteQuery' thread for %s." % self.thread_id)
                    return
        self.running = False
        self.used = True
        logger.info("Terminating 'VoteQuery' thread for %s." % self.thread_id)
        return

cmdtag = '~B[Vote]~B'
threads = {}

def init():
    add_hook('message', message)

def shutdown():
    for thread in threads:
        thread.running = False

def message(irc, channel, origin, command, args):
    global threads
    
    irc_helpers = m('irc_helpers')
    target = channel
    commands = ['vote', 'setvote', 'unvote']
    thread_id = '%s/%s' % (irc.network.name, target)
    
    if command not in commands:
        return
    
    if origin.hostname.find('.lindenlab.com') != -1:
        origin.hostname = '%s@%s' % (origin.nick, origin.hostname)
    
    if thread_id not in threads:
        threads[thread_id] = VoteQuery(thread_id, irc, target)
    
    thread = threads[thread_id]
    
    if thread.used:
        threads[thread_id] = VoteQuery(thread_id, irc, target)
    
    thread = threads[thread_id]
    
    if command == 'vote':
        if len(args) == 0:
            if thread.query != '':
                irc_helpers.message(irc,target,'%s Current query: ~B"%s"~B. (%s seconds left to vote)' % (cmdtag, thread.query, int(round(thread.length - thread.elapsed))))
                for option in thread.options:
                    irc_helpers.message(irc,target,'%s Option ~B#%s:~B "%s" ~B(%s votes)~B' % (cmdtag, option+1, thread.options[option][0], thread.options[option][1]))
                irc_helpers.message(irc,target,'%s Type ~B"!vote <option number>"~B to cast your vote!' % cmdtag)
            else:
                irc_helpers.message(irc,target,'%s There is currently no query for ~B%s~B. (Type ~B"!setvote <query>"~B to start a vote.)' % (cmdtag, thread_id))
        elif thread.query != '':
            if origin.hostname in thread.voted:
                irc_helpers.message(irc,target,'%s You already voted and therefore can not vote again.' % cmdtag)
                return
            try:
                vote = int(args[0].strip('#')) - 1
            except:
                irc_helpers.message(irc,target,'%s ~BInvalid vote; ~B"%s"~B was not a valid option.' % (cmdtag, vote))
                return
            if vote in thread.options:
                thread.options[vote][1] += 1
                irc_helpers.message(irc,target,'%s Your vote has been cast.' % cmdtag)
                thread.voted[origin.hostname] = vote
            else:
                irc_helpers.message(irc,target,'%s Invalid vote; ~B"%s"~B was not a valid option.' % (cmdtag, vote))
        else:
            irc_helpers.message(irc,target,'%s There is currently no vote in query. (Type ~B"!setvote (option1, option2, option3,..ect.) <query>"~B to start a vote. If options are omitted, ~B"Yes"~B and ~B"No"~B are used.)' % cmdtag)
    elif command == 'setvote':
        if len(args) > 0:
            if thread.running:
                irc_helpers.message(irc,target,'%s There is already a vote for ~B%s~B, please wait for the current vote to end before starting a new one.' % (cmdtag, thread_id))
            #We have to do our own parsing and such to parse options from parenthesis, so rejoin the arguments.
            args = " ".join(args)
            if args.find('(') != -1 and args.find(')') != -1:
                temp = args[1+args.find('('):args.find(')')]
                temp = temp.split(',')
                for option in temp:
                    if option.strip() != '':
                        thread.options[len(thread.options)] = [option.strip(), 0]
                if len(thread.options) <= 0:
                    irc_helpers.message(irc,target,"%s You supplied a ~B!setvote~B command that contained the correct syntax for custom options, but didn't actually supply any arguments. Ex. Usage: ~B'!setvote (arg, arg, arg) query'~B." % cmdtag)
                    return
                thread.query = args[1+args.find(')'):]
            else:
                thread.query = args
                thread.options[0] = ['Yes', 0]
                thread.options[1] = ['No', 0]
            thread.start()
            irc_helpers.message(irc,target,'%s The query ~B"%s"~B has been set for ~B%s~B. (~B%s~B seconds left to vote)' % (cmdtag, args, thread_id, int(round(thread.length - thread.elapsed))))
            for option in thread.options:
                    irc_helpers.message(irc,target,'%s Option ~B#%s:~B "%s" ~B(%s votes)~B' % (cmdtag, option+1, thread.options[option][0], thread.options[option][1]))
            irc_helpers.message(irc,target,'%s Type ~B"!vote <option number>"~B to cast your vote!' % cmdtag)
        else:
            irc_helpers.message(irc,target,'%s Please supply a query to vote on.' % (cmdtag))
    elif command == 'unvote':
        if origin.hostname in thread.voted:
            thread.options[thread.voted[origin.hostname]][1] -= 1
            del thread.voted[origin.hostname]
            irc_helpers.message(irc,target,'%s Your vote has been removed from the inquiry and you can now vote again if you wish.' % cmdtag)
        else:
            irc_helpers.message(irc,target,"%s You haven't voted yet." % cmdtag)
            