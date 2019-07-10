import nose.tools as nt

from .. import utils


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
