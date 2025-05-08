class ConsistencyError(Exception):
    """
    Error raise when inconsistency foundbetween administrative state and unit repositories
    or between change and administrative state and unit repositories to which it is applied.
    """
    pass 
