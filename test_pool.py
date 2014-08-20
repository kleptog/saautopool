#!/usr/bin/python

from saautopool import SAAutoPool
from sqlalchemy.pool import QueuePool

import random
import heapq
from collections import namedtuple

RATE=10
DELAY=0.1

Event = namedtuple('Event', 'ts type conn')

stat_real_connections = 0
stat_connections = 0

class TestConnection(object):
    def __init__(self):
        global stat_real_connections
#        print "Real Open"
        stat_real_connections += 1
        
    def close(self):
#        print "Real Close"
        pass
    
    def rollback(self):
        pass

def test_connect():
    return TestConnection()

TIME = 0
SAAutoPool._get_time = lambda self: TIME
pool = SAAutoPool(test_connect, pool_size=50)
#pool = QueuePool(test_connect, pool_size=20)

queue = []

heapq.heappush(queue, Event(0, 1, None))

i = 0

while i < 100000:
    ev = heapq.heappop(queue)

    if ev.type == 1:
        stat_connections += 1
        TIME = ev.ts
        conn = pool.connect()
        heapq.heappush(queue, Event(ev.ts + random.expovariate(RATE), 1, None) )
        heapq.heappush(queue, Event(ev.ts + random.expovariate(1/DELAY), -1, conn) )
    else:
        ev.conn.close()
    i += 1

print "Level mean: %.2f" % pool.mean
print "Est rate: %.1f" % pool.rate
print "Queue size: %d" % pool.qsize
print "Total checkouts: %d" % stat_connections
print "Total real checkouts: %d" % stat_real_connections
#print "Max counter: %d" % pool.max_counter
print "Ratio: %.1f%%" % (100.0 * stat_real_connections / stat_connections)
print "Rate checkouts: %.1f/s" % (float(stat_connections) / pool.last_ts)
print "Rate real checkouts: %.1f/s" % (float(stat_real_connections) / pool.last_ts)

