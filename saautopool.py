import sqlalchemy.pool
import time
import math

class SAAutoPool(sqlalchemy.pool.QueuePool):
    """ A pool class similar to QueuePool but rather than holding some
    minimum number of connections open makes an estimate of how many
    connections are needed.

    The goal is that new connections should be opened at most once every few
    seconds and shouldn't create so many that there will be many idle. """

    def __init__(self, creator, pool_size=20, open_interval=5, **kw):
        """ Create a new SAAutoPool.

        pool_size is passed to to the QueuePool parent. You shouldn't need
        to adjust this, it's more to provide a hard maximum on the number of
        connections.

        open_interval is the target interval between the opening of new
        connections, in seconds.  The default 5 means to aim for opening a
        new connection once every 5 seconds.
        """

        super(SAAutoPool, self).__init__(creator, pool_size=pool_size, **kw)

        self.open_interval = open_interval
        # Start at an expected 5 connections, to avoid large churn on
        # startup.  The 5 is based on the default 5 in QueuePool.
        self.mean = 5
        self.rate = 1
        self.last_ts = self._get_time()

        self.qsize = 1
        self.next_update = 0

        self.decay_rate = math.log(0.5)/60

    def _get_time(self):
        # Internal function to allow overriding, primarily for testing.
        return time.time()

    def _update_qsize(self, ts, checkout):
        # An weighted average, where one minute ago counts half as much.
        w = math.exp( (ts-self.last_ts)*self.decay_rate )
        self.last_ts = ts

        self.rate = w*self.rate
        if checkout:
            self.rate += (1-math.exp(self.decay_rate))

        level = self.checkedout()
        self.mean = w*self.mean + (1-w)*level

        if ts > self.next_update:
            # The idea is that if we know there are 20 checkouts per second,
            # then we want to aim that only 5% of checkouts lead to an
            # actual new connection.  The number of actual connections is
            # tracked by the mean, so by using the inverse CDF of the
            # Poisson distribtion we can calculate how many connections we
            # actually need to acheive this target.

            self.qsize = self._inv_cdf_poisson( 1-(1.0/max(2, self.open_interval*self.rate)), self.mean )
            self.next_update = ts+1

    @staticmethod
    def _inv_cdf_poisson(p, mu):
        """ Stupid simple inverse poisson distribution. Actually 1 too high, but that's OK here """
        x = 0
        n = 0
        while x < p:
            x += math.exp(-mu)*math.pow(mu, n)/math.factorial(n)
            n += 1
        return n

    def _do_get(self):
        self._update_qsize(self._get_time(), True)

        conn = super(SAAutoPool, self)._do_get()

#        print ">>> last_ts=%.1f ci=%d  co=%d=%d-%d+%d  qsize=%d" % (self.last_ts, self.checkedin(), self.checkedout(), self._pool.maxsize, self._pool.qsize(), self._overflow, self.qsize)

        return conn

    def _do_return_conn(self, conn):
        self._update_qsize(self._get_time(), False)

        super(SAAutoPool, self)._do_return_conn(conn)

        # If there's a connection in the pool and the total connections exceeds the limit, close it.
        if self.checkedin() > 0 and self.qsize < self.checkedin() + self.checkedout():
            conn = self._pool.get()
            conn.close()
            # This is needed so the connection level count remains accurate
            self._dec_overflow()
#        print "<<< last_ts=%.1f ci=%d  co=%d=%d-%d+%d  qsize=%d" % (self.last_ts, self.checkedin(), self.checkedout(), self._pool.maxsize, self._pool.qsize(), self._overflow, self.qsize)
