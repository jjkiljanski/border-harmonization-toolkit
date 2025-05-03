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

    # Test for a date within the timespan
    assert timespan1.contains(datetime(1925, 5, 15))  # Date inside the span
    assert timespan2.contains(datetime(1935, 7, 20))  # Date inside the span

    # Test for a date exactly at the boundaries
    assert timespan1.contains(datetime(1923, 1, 1))  # Start date should be inclusive
    assert timespan1.contains(datetime(1930, 12, 31))  # End date should be inclusive

    # Test for a date outside the timespan
    assert not timespan1.contains(datetime(1931, 1, 1))  # Date after timespan1
    assert not timespan2.contains(datetime(1930, 12, 31))  # Date before timespan2

# Test for TimeSpanRegistry class
def test_timespan_registry():
    # Create a TimeSpanRegistry with two time spans
    registry = TimeSpanRegistry(registry=[
        TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31)),
        TimeSpan(start=datetime(1931, 1, 1), end=datetime(1938, 12, 31))
    ])

    # Test if a date is within any of the time spans in the registry
    assert any(ts.contains(datetime(1925, 5, 15)) for ts in registry.registry)  # Should be in first time span
    assert any(ts.contains(datetime(1935, 7, 20)) for ts in registry.registry)  # Should be in second time span

    # Test if a date is not within any of the time spans in the registry
    assert not any(ts.contains(datetime(1939, 1, 1)) for ts in registry.registry)  # Should not be in any timespan

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
