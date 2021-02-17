from test.unittests.mocks import base_config  # For backwards compatibility


class Anything:
    """Class matching any object.

    Useful for assert_called_with arguments.
    """
    def __eq__(self, other):
        return True
