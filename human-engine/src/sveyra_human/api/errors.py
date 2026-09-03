"""Engine error types."""


class SveyraHumanError(Exception):
    """Base for every error this package raises."""


class NotImplementedYetError(SveyraHumanError):
    """A layer that is designed but not built yet.

    Distinct from NotImplementedError so callers can tell a phase boundary
    apart from a genuine abstract-method violation.
    """


class InvalidInputError(SveyraHumanError):
    """Caller supplied something the engine cannot work with."""


class ReconstructionError(SveyraHumanError):
    """Fitting ran but did not converge to a usable body."""
