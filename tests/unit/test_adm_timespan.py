import pytest
from datetime import datetime
from pydantic import ValidationError
from ...data_models.adm_timespan import TimeSpan, TimeSpanRegistry

# Test data for the TimeSpan class
def test_timespan():
    # Create time spans for testing
    timespan1 = TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    timespan2 = TimeSpan(start=datetime(1931, 1, 1), end=datetime(1938, 12, 31))

    # Verify the correctness of the string representation
    assert str(timespan1) == "(1923-01-01, 1930-12-31)"
    assert str(timespan2) == "(1931-01-01, 1938-12-31)"

    # Test that both timespans have a correctly initialized 'middle' attribute
    assert (timespan1.start < timespan1.middle < timespan2.end) or (timespan1.start == timespan1.middle == timespan2.end)
    assert (timespan2.start < timespan2.middle < timespan2.end) or (timespan2.start == timespan2.middle == timespan2.end)

def test_timespan_contains():
    # Create time spans for testing
    timespan1 = TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    timespan2 = TimeSpan(start=datetime(1931, 1, 1), end=datetime(1938, 12, 31))

    # Test for a date within the timespan
    assert datetime(1925, 5, 15) in timespan1  # Date inside the span
    assert datetime(1935, 7, 20) in timespan2  # Date inside the span

    # Test for a date exactly at the boundaries
    assert datetime(1923, 1, 1) in timespan1  # Start date should be inclusive
    assert datetime(1930, 12, 31) not in timespan1  # End date should not be inclusive

    # Test for a date outside the timespan
    assert datetime(1931, 1, 1) not in timespan1  # Date after timespan1
    assert datetime(1930, 12, 31) not in timespan2  # Date before timespan2

    timespan3 = TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 30))
    timespan4 = TimeSpan(start=datetime(1923, 1, 1), end=datetime(1931, 1, 1))
    timespan5 = TimeSpan(start=datetime(1923, 1, 2), end=datetime(1930, 12, 31))
    timespan6 = TimeSpan(start=datetime(1922, 12, 31), end=datetime(1930, 12, 31))
    timespan7 = TimeSpan(start=datetime(1923, 1, 2), end=datetime(1930, 12, 30))
    timespan8 = TimeSpan(start=datetime(1922, 12, 31), end=datetime(1931, 1, 1))

    assert timespan3 in timespan1
    assert timespan4 not in timespan1
    assert timespan5 in timespan1
    assert timespan6 not in timespan1
    assert timespan7 in timespan1
    assert timespan8 not in timespan1

# Test for TimeSpanRegistry class
def test_timespan_registry():
    # Create a TimeSpanRegistry with two time spans
    registry = TimeSpanRegistry(registry=[
        TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31)),
        TimeSpan(start=datetime(1931, 1, 1), end=datetime(1938, 12, 31))
    ])

    # Test if a date is within any of the time spans in the registry
    assert any(datetime(1925, 5, 15) in ts for ts in registry.registry)  # Should be in first time span
    assert any(datetime(1935, 7, 20) in ts for ts in registry.registry)  # Should be in second time span

    # Test if a date is not within any of the time spans in the registry
    assert not any(datetime(1939, 1, 1) in ts for ts in registry.registry)  # Should not be in any timespan

# Test for invalid data input (e.g., bad dates or missing fields)
def test_invalid_timespan():
    with pytest.raises(ValidationError):
        # TimeSpan missing the 'start' field
        TimeSpan(start=None, end=datetime(1930, 12, 31))

    with pytest.raises(ValidationError):
        # TimeSpan with 'end' earlier than 'start'
        TimeSpan(start=datetime(1931, 1, 1), end=datetime(1923, 1, 1))

    with pytest.raises(ValidationError):
        # TimeSpan with 'end' same as 'start'
        TimeSpan(start=datetime(1931, 1, 1), end=datetime(1931, 1, 1))
