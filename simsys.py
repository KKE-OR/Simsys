#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2013 KOZO Keikaku Engineering Inc

import math, os, sys, time
from bisect import bisect
from random import expovariate, random, seed

class simsys(object):
	"""シミュレーション"""
	wait, get, back = range(3)
	@staticmethod
	def reset(iseed = None, debug = False):
		if (iseed): seed(iseed)
		simsys.debug = debug
		simsys.now = 0.0
		simsys.limit = sys.float_info.max
		simsys.stop = False
		simsys.events = []
	@staticmethod
	def do(eve, *args):
		simsys.next(None, eve(*args))
	@staticmethod
	def doat(tm, eve, *args):
		simsys.do(simsys._doatev, eve, tm, *args)
	@staticmethod
	def _doatev(eve, tm, *args):
		yield simsys.wait, tm
		eve(*args)
	@staticmethod
	def next(tm, it):
		if (tm > 0): simsys.now = tm
		simsys.stop = simsys.now > simsys.limit
		if (simsys.stop): return
		try:
			while 1:
				val = it.next() # act, tm | obj
				if (val[0] == simsys.wait):
					ev = (simsys.now + val[1], it)
					simsys.events.insert(bisect(simsys.events, ev), ev)
				elif (val[0] == simsys.get):
					if (val[1].get(it)): continue
				elif (val[0] == simsys.back):
					val = val[1].back()
					if (val != None): simsys.events.insert(0, (simsys.now, val))
					continue
				break
		except StopIteration: pass
		except Exception as e:
			print e
	@staticmethod
	def start(limit):
		simsys.limit = limit
		while not simsys.stop and len(simsys.events) > 0:
			try:
				ev = simsys.events.pop(0)
				simsys.next(*ev)
			except: pass
	@staticmethod
	def log(p):
		if (simsys.debug): print p
class simres:
	"""リソース"""
	def __init__(self, capa):
		self.capacity = capa
		self.use = 0
		self.wlist = []
	def get(self, it):
		if (self.use >= self.capacity):
			self.wlist.append(it)
			return False
		self.use += 1
		return True
	def back(self):
		if (len(self.wlist) > 0): return self.wlist.pop(0)
		self.use -= 1
		return None

class simstat(object):
	"""観測統計量"""
	def __init__(self):
		self._value = 0.0
		self.reset()
	def reset(self):
		self.count, self._value, self.sum, self.sum2 = 0, 0.0, 0.0, 0.0
		self.max = sys.float_info.min
		self.min = sys.float_info.max
	def ave(self): return 0 if self.count == self._value else self.sum / self.count
	def var(self):
		a = self.ave()
		return 0.0 if self.count <= 1 else max(0.0, (self.sum2 - a * a * self.count) / (self.count - 1))
	def std(self): return math.sqrt(self.var())
	def getvalue(self): return self._value
	def setvalue(self, val):
		self.count += 1
		self._value = val
		if (val > self.max): self.max = val
		if (val < self.min): self.min = val
		self.sum += val
		self.sum2 += val * val
	value = property(getvalue, setvalue)
class simstattime(simstat):
	"""経時統計量"""
	def __init__(self):
		simstat.__init__(self)
		self.stim = self.ptim = simsys.now
	def reset(self):
		pre = self._value
		simstat.reset(self)
		self.max = self.min = self._value = pre
		# 開始時刻, 設定時刻
		self.stim = self.ptim = simsys.now
	def ave(self):
		if (self.ptim != simsys.now):
			self.value = self._value
			--self.count
		return 0.0 if self.stim == self.ptim else self.sum / (self.ptim - self.stim)
	def var(self):
		if (self.stim == self.ptim): return 0.0
		a = self.ave()
		return max(0.0, self.sum2 / (self.ptim - self.stim) - a * a)
	def setvalue(self, val):
		v = self._value * (simsys.now - self.ptim)
		self.ptim = simsys.now
		self.sum += v - val
		self.sum2 += v * self._value - val * val
		simstat.setvalue(self, val)
	value = property(simstat.getvalue, setvalue)

class queue:
	def __init__(self, rate):
		self.rate = rate
		self.waiting = []
		self.busy = simstattime()
		self.len = simstattime()
		self.intime = simstat()
	def resetstat(self):
		self.busy.reset();
		self.len.reset();
		self.intime.reset();
	def push(self, c):
		self.waiting.append(c)
		self.len.value += 1
		if len(self.waiting) > 1: return
		while len(self.waiting) > 0:
			self.busy.value = 1
			c = self.waiting[0]
			simsys.log('%.2f service %d' % (simsys.now, c[0]))
			yield simsys.wait, expovariate(self.rate)
			self.intime.value = simsys.now - c[1]
			self.waiting.pop(0)
			self.len.value -= 1
			simsys.log('%.2f terminate %d' % (simsys.now, c[0]))
		self.busy.value = 0
class arrival_timer:
	count = 0
	def __init__(self, queue, rate):
		self.queue = queue
		self.rate = rate
	def arrival(self):
		while 1:
			yield simsys.wait, expovariate(self.rate)
			arrival_timer.count += 1
			simsys.log('%.2f arrive %d' % (simsys.now, arrival_timer.count))
			simsys.do(self.queue.push, (arrival_timer.count, simsys.now))
def test():
	simsys.reset(8)
	ar, sr = 3.0, 4.0
	ro = ar / sr
	que = queue(sr)
	atmr = arrival_timer(que, ar)
	simsys.do(atmr.arrival)
	simsys.start(10000)
	print u'理論:平均稼働率= %.3f, 系内数 = %.3f, 系内時間 = %.3f' % (ro, ro/ (1 - ro), 1 / (sr - ar))
	print u'シム:平均稼働率= %.3f, 系内数 = %.3f, 系内時間 = %.3f' % (que.busy.ave(), que.len.ave(), que.intime.ave())
	print 'Press Enter'
	sys.stdin.readline()
def func1():
	print 'A' # 0
	yield simsys.wait, 2
	print 'B' # 2
def func2():
	yield simsys.wait, 1
	print 'C' # 1
	yield simsys.wait, 2
	print 'D' # 3
def sample():
	simsys.reset()
	simsys.do(func1)
	simsys.do(func2)
	simsys.start(3)
	
if __name__ == '__main__': test()