#!/usr/bin/python

from saautopool import SAAutoPool
from sqlalchemy.pool import QueuePool

import random
import heapq
from collections import namedtuple

Event = namedtuple('Event', 'ts type conn')

class TestConnection(object):
    stat_real_connections = 0

    def __init__(self):
        TestConnection.stat_real_connections += 1

    def close(self):
        pass

    def rollback(self):
        pass

def test_connect():
    return TestConnection()

SAAutoPool._get_time = lambda self: PoolTester.TIME
class PoolTester(object):
    TIME = 0

    def run_test(self, RATE, DELAY):
        stat_connections = 0
        TestConnection.stat_real_connections = 0
        PoolTester.TIME = 0

        pool = SAAutoPool(test_connect, pool_size=50)

        queue = []

        heapq.heappush(queue, Event(0, 1, None))

        i = 0

        while i < 100000:
            ev = heapq.heappop(queue)
            PoolTester.TIME = ev.ts

            if ev.type == 1:
                stat_connections += 1
                conn = pool.connect()
                heapq.heappush(queue, Event(ev.ts + random.expovariate(RATE), 1, None) )
                heapq.heappush(queue, Event(ev.ts + random.expovariate(1.0/DELAY), -1, conn) )
            else:
                ev.conn.close()
            i += 1

        stat_real_connection = TestConnection.stat_real_connections

        results=dict(
            est_mean=pool.mean,
            est_rate=pool.rate,
            rate=RATE,
            delay=DELAY,
            qsize=pool.qsize,
            real_checkouts=TestConnection.stat_real_connections,
            checkouts=stat_connections,
            ratio=float(TestConnection.stat_real_connections) / stat_connections,
            total_time=pool.last_ts,
            connect_interval=pool.last_ts / TestConnection.stat_real_connections,
        )

#        print "Est mean: %.2f    (expect %f)" % (pool.mean, RATE*DELAY)
#        print "Est rate: %.1f    (expect %f)" % (pool.rate, RATE)
#        print "Queue size: %d" % pool.qsize
#        print "Total checkouts: %d" % stat_connections
#        print "Total real checkouts: %d" % TestConnection.stat_real_connections

#        print "Ratio: %.1f%%" % (100.0 * TestConnection.stat_real_connections / stat_connections)
#        print "Rate checkouts: %.1f/s" % (float(stat_connections) / pool.last_ts)
#        print "Rate real checkouts: %.1f/s" % (float(TestConnection.stat_real_connections) / pool.last_ts)

        return results

STATS = {}

for i in range(-3, 5):
    rate = 2**i
    print "%5.3f  " % rate,
    for j in range(-3, 5):
        delay = 2**j
        if rate*delay > 25:
            break
        STATS[(i,j)] = res = PoolTester().run_test(rate, delay)

#        print "%5.2f%%  " % (res['ratio']*100.0),
#        print "%5.1fs  " % (res['connect_interval']),
        print "%3d  " % (res['qsize']),
    print
