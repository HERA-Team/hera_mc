import nose.tools as nt
from astropy.time import Time
from astropy.units import Quantity
from .. import utils

sidesec = Quantity(1, 'sday').to('day').value  # length of sidereal second in SI seconds.


def test_LSTScheduler_lstbinsize():
    """
    test that two bins have the right time separation
    """
    LSTbin_size = 10
    starttime1 = Time('2019-9-19T05:05:05.0', format='isot', scale='utc')
    scheduletime1, hour1 = utils.LSTScheduler(starttime1, LSTbin_size)
    starttime2 = Time('2019-9-19T05:05:15.0', format='isot', scale='utc')
    scheduletime2, hour2 = utils.LSTScheduler(starttime2, LSTbin_size)
    nt.assert_almost_equal((hour2 - hour1).hour * 3600, LSTbin_size)
    nt.assert_almost_equal((scheduletime2 - scheduletime1).value * 24 * 3600,
                           LSTbin_size * sidesec, places=5)


def test_LSTScheduler_multiday():
    """
    test that two bins are at the same LST on different days
    """
    LSTbin_size = 10
    starttime1 = Time('2019-9-19T05:04:00.0', format='isot', scale='utc')
    scheduletime1, hour1 = utils.LSTScheduler(starttime1, LSTbin_size)
    # lst is 4 minutes earlier every day
    starttime2 = Time('2019-9-20T05:00:0.0', format='isot', scale='utc')
    scheduletime2, hour2 = utils.LSTScheduler(starttime2, LSTbin_size)
    nt.assert_almost_equal((hour2.hour - hour1.hour) * 3600, 0)


def test_reraise_context():
    with nt.assert_raises(ValueError) as cm:
        try:
            raise ValueError('Initial Exception message.')
        except ValueError:
            utils._reraise_context('Add some info')
    ex = cm.exception
    nt.assert_equal(ex.args[0], 'Add some info: Initial Exception message.')

    with nt.assert_raises(ValueError) as cm:
        try:
            raise ValueError('Initial Exception message.')
        except ValueError:
            utils._reraise_context('Add some info %s', 'and then more')
    ex = cm.exception
    nt.assert_equal(ex.args[0], 'Add some info and then more: Initial Exception message.')

    with nt.assert_raises(EnvironmentError) as cm:
        try:
            raise EnvironmentError(1, 'some bad problem')
        except EnvironmentError:
            utils._reraise_context('Add some info')
    ex = cm.exception
    nt.assert_equal(ex.args[1], 'Add some info: some bad problem')
