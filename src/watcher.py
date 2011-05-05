#!/usr/bin/env python

import sys, time
from daemon import Daemon
from watcherproc import WatcherProc

class Watcher(Daemon):
	w = WatcherProc()
	
	def run(self):
		if self.w.connect():
			while True:	self.w.check()

if __name__ == "__main__":
	daemon = Watcher('/var/run/vcon-watcher.pid')
	if len(sys.argv) > 1:
		action = sys.argv[1]
		if action in ["start", "stop", "restart"]:
			getattr(daemon, action)()
		else:
			print "usage: %s start|stop|restart" % sys.argv[0]
			sys.exit(2)
	else:
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(1)
