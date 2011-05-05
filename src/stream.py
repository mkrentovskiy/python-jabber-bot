import sqlite3, urllib, re
from config import Config

class Stream(object):
    db = None
    
    ID = 0
    URL = 1
    TYPE = 2
    STATE = 3
    FILTERS = 4
    EN = 5
    
    def __init__(self):
        self.db = sqlite3.connect(Config.DATABASE)
    
    def close(self):
        self.db.close() 

    # working
    def getWorkingStreams(self):
        c = self.db.cursor()
        c.execute('SELECT * FROM streams WHERE en=1')
        return c.fetchall()
    
    def saveState(self, id, state):
        c = self.db.cursor()
        c.execute('UPDATE streams SET state=? WHERE id=?', (state, id))
        self.db.commit()        
        return
    
    # interface    
    def addStream(self, url):
        d = urllib.urlopen(url)    
        print     
        if d and d.getcode() == 200:            
            if re.search('(rss|atom|feed|xml)', str(d.info())): t = 1
            else: t = 2        
  
            c = self.db.cursor()
            c.execute('INSERT INTO streams (url,type,en) VALUES (?, ?, 1)', (url, t))
            self.db.commit()
            
            return "Stream " + url + " added"
        else:
            return "Unable to open URL " + url
    
    def delStream(self, id):
        idd = self.convId(id)
        if idd > 0:
            c = self.db.cursor()
            c.execute('DELETE FROM streams WHERE id=%d' % idd)
            self.db.commit()        
            return "Stream with id " + str(id) + " deleted"
        else:
            return "Param parsing error"
        
    def listStreams(self):
        r = "Streams:\n"         
        c = self.db.cursor()
        c.execute('SELECT id, url, type, en FROM streams ORDER BY en, id')
        for i in c.fetchall():
            if i[2] == 1: type = " RSS"
            else: type = "PAGE"
            if i[3] == 1: en = "+";
            else: en = "-" 
            r += "[%5d] [%s] [%s] %s\n" % (i[0], type, en, i[1])          
        return r 
    
    def pauseStream(self, id):
        idd = self.convId(id)
        if idd > 0:
            c = self.db.cursor()
            c.execute('UPDATE streams SET en=0 WHERE id=%d' % idd)
            self.db.commit()
            return "Stream with id " + str(id) + " paused"
        else:
            return "Param parsing error"
      
    def startStream(self, id):        
        idd = self.convId(id) 
        if idd > 0:               
            c = self.db.cursor()
            c.execute('UPDATE streams SET en=1 WHERE id=%d' % idd)
            self.db.commit()        
            return "Stream with id " + str(id) + " started"
        else:
            return "Param parsing error"
        
    #utils
    def convId(self, id):
        if re.match("^[0-9]*$", id.strip()): return int(id.strip())
        else: return 0   
                 