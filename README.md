SAAutoPool
==========

The default SQLAlchemy connection pool is the QueuePool, which is a simple
connection pool that stores up to five connections by default.  This is
suboptimal in two ways:

  - On a largely idle client this ends up holding several connections open
    to the database that are not often used. These idle connections are a
    (small) cost on the database server.

  - On a busy server that actually needs more than 5 connections it can lead
    to irregular opening an closing of connections, when it might actually
    benefit from a larger pool.

Clearly such a simple queue cannot handle all cases. For specific programs
it would be possible to tune the pool size, but when writing a general peice
of software that does not know its expected load beforehand this just
becomes another knob to twiddle.

Hence the SAAutoPool, which monitors the usage of the pool and tries to
optimise the pool size based on the criteria that it's OK to occasionally
open new connections, but that it's also important to not have connections
idle for a long time.

Algorithm
=========

To achieve this goal SAAutoPool tracks two statistics: the number of checked
out connections and the rate of checkouts per second.  A pool size is then
calculated such that a new connection might be opened on average about once
every (by default) ten seconds.

The numbers of checked out connection and rate are calculated as a sort of
weighted average with exponential decay, such that the level a minute ago
counts half as much as the level now.

Then to calculate the queue size we need to know a little queueing theory. 
Basically this is a queueing problem with potentially unlimited servers, a
so called M/M/infinity queue.  The probability distribution for this is the
Poisson distribution, where the parameter is the average number of checked
out connections.  Then if we want to statistically open a new connection
once every ten seconds, we need to calculate the level such that:

   P(open connections > level) < 1/(10*(checkout rate per second))

Hence there is a simple inverse Poission distribution function which is used
once a second to recalculate the level.
