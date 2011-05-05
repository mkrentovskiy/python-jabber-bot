# -*- encoding: utf-8 -*-

import time, json, re, urllib, logging
import jabber, feedparser

from stream import Stream
from config import Config

class WatcherProc(object):
    jc = jabber.Client(host=Config.BOT_SRVR)
    stream = Stream()
    
    def connect(self):
        r = True
        try: self.jc.connect()
        except IOError: r = False
        if r:
            self.jc.registerHandler('message',self.jcbMessage)
            self.jc.registerHandler('presence',self.jbcPresence)
            self.jc.registerHandler('iq',self.jbcIq)

            if self.jc.auth(Config.BOT_USER,Config.BOT_PASS,Config.BOT_LOCT):  
                self.jc.requestRoster()
            else:
                r = False
        return r                    
        
    def disconnect(self):
        self.jc.disconnect()    
        self.stream.close()            
        
    def check(self):        
        self.jc.process()        
        self.setJabberState("Working!")
        
        strs = self.stream.getWorkingStreams()        
        for s in strs:
            if s[Stream.TYPE] == 1: self.parseRSS(s)                 
            elif s[Stream.TYPE] == 2: self.parsePage(s)
        
        self.setJabberState("Waiting")        
        for i in range(1, 300):
            self.jc.process()        
            time.sleep(1) 
    
    def parseRSS(self, s):
        if s[Stream.STATE]: state = json.loads(s[Stream.STATE])
        else: state = []        
        #filters = json.loads(s[Stream.FILTERS])
        d = feedparser.parse(s[Stream.URL])
        if d:
            newState = []
            for e in d.entries:
                if e and hasattr(e, 'id'):
            	    if (not e.id in state) and len(state) > 0:
                	link = re.sub(' ', '', e.link)
                	self.sendJabberMessage(u"%s\n%s" % (e.title, link))
            	    newState.append(e.id)                    
            self.stream.saveState(s[Stream.ID], json.dumps(newState))
        else:
            self.sendJabberMessage("Error loading RSS stream - " + s[Stream.URL])
            
        
    def parsePage(self, s):
        if s[Stream.STATE]: state = s[Stream.STATE]
        else: state = ""
        p = urllib.urlopen(s[Stream.URL])
        if p and p.getcode() == 200:
            pi = p.read()        
            pt = re.search("<title>([^<]*)</title>", pi)
            if pt:
                newState = unicode(pt.group(1).decode("cp1251").strip())
                needSave = True
                if state:
                    if state <> newState and len(newState) > 16: 
                        self.sendJabberMessage(u"%s\n%s" % (newState, s[Stream.URL]))                    
                    else: needSave = False
                if needSave: self.stream.saveState(s[Stream.ID], newState)                    
            else: 
                self.sendJabberMessage("Error parsing page stream - " + s[Stream.URL])
        else:
            self.sendJabberMessage("Error loading page stream - " + s[Stream.URL])
        
        
    def jcbMessage(self, c, msg): 
        if msg.getBody() and msg.getFrom().getStripped() in Config.NOTIFY:
            self.parseJabberMessage(msg.getBody(), msg.getFrom())

    def jbcPresence(self, c, prs):
        who = str(prs.getFrom())
        type = prs.getType()        
        if type == 'subscribe':
            c.send(jabber.Presence(to=who, type='subscribed'))
            c.send(jabber.Presence(to=who, type='subscribe'))
        elif type == 'unsubscribe':
            c.send(jabber.Presence(to=who, type='unsubscribed'))
            c.send(jabber.Presence(to=who, type='unsubscribe'))
    
    def jbcIq(self, con, iq):
        pass                
        
    def setJabberState(self, state):
        p = jabber.Presence()
        p.setStatus(state)
        self.jc.send(p)

    def sendJabberMessage(self, text):
        for r in Config.NOTIFY:
            t = self.stripXML(text.strip())
            msg = jabber.Message(r, t)
            msg.setType('chat')
            self.jc.send(msg)

    def sendJabberMessageTo(self, to, text):
        t = self.stripXML(text.strip().encode("utf-8"))
        msg = jabber.Message(to, t)
        msg.setType('chat')
        self.jc.send(msg)
        self.jc.process()
            
    def parseJabberMessage(self, str, fr):
        cmd = str.split()        
        if cmd[0] == 'ADD':
            self.sendJabberMessageTo(fr, self.stream.addStream(cmd[1].strip()))
        elif cmd[0] == 'DEL': 
            self.sendJabberMessageTo(fr, self.stream.delStream(cmd[1].strip()))            
        elif cmd[0] == 'LIST':
            self.sendJabberMessageTo(fr, self.stream.listStreams())
        elif cmd[0] == 'PAUSE': 
            self.sendJabberMessageTo(fr, self.stream.pauseStream(cmd[1].strip()))            
        elif cmd[0] == 'START': 
            self.sendJabberMessageTo(fr, self.stream.startStream(cmd[1].strip()))            
        else:
            self.sendJabberMessageTo(fr, "commands are\nADD [stream URL] - add stream to list\nLIST - show streams with ID\nDEL [id] - delete stream with id\nPAUSE [id] - stop watching stream with id\nSTART [id] - start wathching stream with id")

    def stripXML(self, s):
        def fixup(m):
            text = m.group(0)
            if text[:1] == "<":
                if text[1:3] == 'br':
                    return '\n'
                else:
                    return "" # ignore tags
            if text[:2] == "&#":
                try:
                    if text[:3] == "&#x":
                        return chr(int(text[3:-1], 16))
                    else:
                        return chr(int(text[2:-1]))
                except ValueError:
                    pass
            elif text[:1] == "&":
                import htmlentitydefs
                if text[1:-1] == "mdash":
                    entity = " - "
                elif text[1:-1] == "ndash":
                    entity = "-"
                elif text[1:-1] == "hellip":
                    entity = "-"
                else:
                    entity = htmlentitydefs.entitydefs.get(text[1:-1])
                if entity:
                    if entity[:2] == "&#":
                        try:
                            return chr(int(entity[2:-1]))
                        except ValueError:
                            pass
                    else:
                        return entity
            return text # leave as is
        ret =  re.sub("(?s)<[^>]*>|&#?\w+;", fixup, s)
        return re.sub("\n+", '\n' , ret)            
        
if __name__ == "__main__":
    w = WatcherProc()
    if w.connect():
        while True: w.check()
        w.disconnect()
    