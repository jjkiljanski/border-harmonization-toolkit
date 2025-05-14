import pytest
from datetime import datetime
from ...data_models.adm_timespan import TimeSpan
from ...data_models.adm_unit import *

############################################################################
#                           UnitState class tests                          #
############################################################################

# Test for UnitState class initialization and basic functionality
def test_unit_state_initialization():
    state = UnitState(
        current_name="District A",
        current_seat_name="Seat A",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    )
    
    assert state.current_name == "District A"
    assert state.current_seat_name == "Seat A"
    assert state.timespan.start == datetime(1923, 1, 1)
    assert state.timespan.end == datetime(1930, 12, 31)

############################################################################
#                            Unit class tests                              #
############################################################################

# Test for Unit class validation (check if name_id is in name_variants)
def test_check_unit_name_in_variants():
    unit = Unit(
        name_id="unit1",
        name_variants=["unit1", "unitA", "unitB"],
        seat_name_variants=["seatA", "seatB"],
        states=[],
    )
    # This should not raise an error because name_id is in name_variants
    unit.check_unit_name_in_variants()

    with pytest.raises(ValueError, match="name_id 'unitX' must be in name_variants"):
        unit_invalid = Unit(
            name_id="unitX",
            name_variants=["unit1", "unitA", "unitB"],
            seat_name_variants=["seatA", "seatB"],
            states=[],
        )
        unit_invalid.check_unit_name_in_variants()

# Test for find_state_by_date method
def test_find_state_by_date():
    state1 = UnitState(
        current_name="District A",
        current_seat_name="Seat A",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    )
    state2 = UnitState(
        current_name="District B",
        current_seat_name="Seat B",
        current_dist_type="m",
        timespan=TimeSpan(start=datetime(1931, 1, 1), end=datetime(1938, 12, 31))
    )
    unit = Unit(
        name_id="unit1",
        name_variants=["unit1", "unitA", "unitB"],
        seat_name_variants=["seatA", "seatB"],
        states=[state1, state2],
    )

    # Test: should find the state that contains the date 1925-06-15
    state = unit.find_state_by_date(datetime(1925, 6, 15))
    assert state == state1  # It should return the first state

    # Test: should return None for a date outside the time range
    state = unit.find_state_by_date(datetime(1939, 1, 1))
    assert state is None

# Test for find_state_by_timespan method
def test_find_state_by_timespan():
    state1 = UnitState(
        current_name="District A",
        current_seat_name="Seat A",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    )
    state2 = UnitState(
        current_name="District B",
        current_seat_name="Seat B",
        current_dist_type="m",
        timespan=TimeSpan(start=datetime(1931, 1, 1), end=datetime(1938, 12, 31))
    )
    unit = Unit(
        name_id="unit1",
        name_variants=["unit1", "unitA", "unitB"],
        seat_name_variants=["seatA", "seatB"],
        states=[state1, state2],
    )

    # Test: should return the correct state based on the timespan
    ts = TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    state = unit.find_state_by_timespan(ts)
    assert state == state1  # It should return the first state

    # Test: should return None if no state matches the timespan
    ts_invalid = TimeSpan(start=datetime(1939, 1, 1), end=datetime(1940, 12, 31))
    state = unit.find_state_by_timespan(ts_invalid)
    assert state is None

# Test for create_next_state method
def test_create_next_state():
    state1 = UnitState(
        current_name="District A",
        current_seat_name="Seat A",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    )
    unit = Unit(
        name_id="unit1",
        name_variants=["unit1", "unitA", "unitB"],
        seat_name_variants=["seatA", "seatB"],
        states=[state1],
    )

    # Test: valid date within an existing state's timespan (1925-06-15)
    old_state, new_state = unit.create_next_state(datetime(1925, 6, 15))

    assert old_state == unit.states[-2] # The returned new state should be the last one in the unit states list
    assert old_state.current_name == "District A"  # Check name correctness
    assert old_state.timespan.start == datetime(1923, 1, 1)  # The old state should start at 1923-01-01
    assert old_state.timespan.end == datetime(1925, 6, 15)  # The end date should match change date
    
    assert new_state == unit.states[-1] # The returned new state should be the last one in the unit states list
    assert new_state.current_name == "District A"  # The name should be the same as the previous state
    assert new_state.timespan.start == datetime(1925, 6, 15)  # The new state should start at 1925-06-15
    assert new_state.timespan.end == datetime(1930, 12, 31)  # The end date should match start date for now
    
    assert len(unit.states) == 2  # There should be two states now

    # Test: invalid date (1931-01-01) outside the existing state's timespan
    with pytest.raises(ValueError, match="Invalid date: 1931-01-01. No state covers this date."):
        unit.create_next_state(datetime(1931, 1, 1))

# Test for abolish method
def test_abolish():
    state1 = UnitState(
        current_name="District A",
        current_seat_name="Seat A",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    )
    unit = Unit(
        name_id="unit1",
        name_variants=["unit1", "unitA", "unitB"],
        seat_name_variants=["seatA", "seatB"],
        states=[state1],
    )

    # Test: abolish the unit on 1930-12-31
    old_state = unit.abolish(datetime(1928, 12, 31))

    assert old_state is state1 # The method should return the ended state.
    assert state1.timespan.end == datetime(1928, 12, 31)  # The end date should be set to 1930-12-31
    assert state1.timespan.start <= state1.timespan.middle <= state1.timespan.end # The middle was updated

# Test for exists method
def test_exists():
    state1 = UnitState(
        current_name="District A",
        current_seat_name="Seat A",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 12, 31))
    )
    unit = Unit(
        name_id="unit1",
        name_variants=["unit1", "unitA", "unitB"],
        seat_name_variants=["seatA", "seatB"],
        states=[state1],
    )

    # Test: check that the unit exists on 1929-12-31 and that it doesn't on 1931-12-31.
    assert unit.exists(datetime(1929,12,31))
    assert not unit.exists(datetime(1931, 12, 31))


############################################################################
#                         UnitRegistry class tests                         #
############################################################################
# Test data setup
def create_test_units():
    state1 = UnitState(
        current_name="District A",
        current_seat_name="Seat A",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 1, 1))
    )
    state2 = UnitState(
        current_name="District B",
        current_seat_name="Seat A",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1930, 1, 1), end=datetime(1938, 1, 1))
    )
    unit1 = Unit(
        name_id="unit1",
        name_variants=["unit1", "unitA", "unitB", "unitS"], # Name "unitS" is shared between unit1 and unit2
        seat_name_variants=["seatA", "seatB", "seatS"], # Name "seatS" is shared between unit1 and unit2
        states=[state1, state2],
    )
    state3 = UnitState(
        current_name="District B",
        current_seat_name="Seat B",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1930, 1, 1))
    )
    unit2 = Unit(
        name_id="unit2",
        name_variants=["unit2", "unitC", "unitD", "unitS"], # Name "unitS" is shared between unit1 and unit2
        seat_name_variants=["seatC", "seatD", "seatS"], # Name "seatS" is shared between unit1 and unit2
        states=[state3],
    )
    return unit1,unit2

# Test for find_unit method
def test_find_unit():
    unit1,unit2 = create_test_units()
    registry = UnitRegistry(unit_list=[unit1,unit2])
    
    # Test: find a unit by name variant
    found_unit = registry.find_unit("unitA")
    assert found_unit == unit1  # Should find the unit

    # Test: find a unit by another name variant
    found_unit = registry.find_unit("unitB")
    assert found_unit == unit1  # Should also find the unit

    # Test: should return None when no unit is found
    found_unit = registry.find_unit("unitX")
    assert found_unit is None  # No such unit

    # Test: find a unit by seat name variant
    found_unit = registry.find_unit("seatB")
    assert found_unit is unit1  # No such unit
    
    # Test: should return None when unit is searched by seat and 'use_seat_names' set to False
    found_unit = registry.find_unit("seatB", use_seat_names=False)
    assert found_unit is None  # No such unit

    # Test: should return None when unit searched by inexistent seat name
    found_unit = registry.find_unit("seatX")
    assert found_unit is None # Should find the unit

    # Test: should return None when unit searched by a shared name "unitS"
    found_unit = registry.find_unit("seatS")
    assert found_unit is None # Should find the unit

    # Test: should return None when unit searched by a shared seat name "seatS"
    found_unit = registry.find_unit("seatS")
    assert found_unit is None # Should find the unit

    # Test: should return BOTH units when unit searched by a shared name "unitS"
    # and allow_non_unique is True
    found_units = registry.find_unit("seatS", allow_non_unique=True)
    assert isinstance(found_units, list)
    assert found_units == [unit1, unit2] # Should find both units

    # Test: should return BOTH units when unit searched by a shared seat name "seatS"
    # and allow_non_unique is True
    found_units = registry.find_unit("seatS", allow_non_unique=True)
    assert isinstance(found_units, list)
    assert found_units == [unit1,unit2] # Should find the unit

    # Test: should None when unit searched by a shared seat name "seatS",
    # allow_non_unique is True, BUT use_seat_names is False
    found_units = registry.find_unit("seatS", use_seat_names=False, allow_non_unique=True)
    assert found_units is None # Should find the unit

# Test for find_unit_state_by_date method
def test_find_unit_state_by_date():
    expected_unit, _ = create_test_units()
    registry = UnitRegistry(unit_list=[expected_unit])
    
    # Test: find a unit state by a date within the first state period
    unit, unit_state, timespan = registry.find_unit_state_by_date("unitA", datetime(1925, 6, 15))
    assert unit == expected_unit  # The correct unit should be returned
    assert unit_state.current_name == "District A"  # The state should match the correct name
    assert timespan.start == datetime(1923, 1, 1)  # The timespan start date should match

    # Test: find a unit state by a date within the second state period
    unit, unit_state, timespan = registry.find_unit_state_by_date("unitB", datetime(1935, 7, 20))
    assert unit == expected_unit  # The correct unit should be returned
    assert unit_state.current_name == "District B"  # The state should match the correct name
    assert timespan.start == datetime(1930, 1, 1)  # The timespan start date should match

    # Test: searching for a (unit, date), where unit exists, but date is outside any of its state ranges
    # Should return (expected_unit, None, None)
    unit, unit_state, timespan = registry.find_unit_state_by_date("unitA", datetime(1940, 1, 1))
    assert unit == expected_unit  # A unit should be found
    assert unit_state is None  # No unit state should be found
    assert timespan is None  # No timespan should be found

    # Test: searching for a non-existing unit should return (None, None, None)
    unit, unit_state, timespan = registry.find_unit_state_by_date("unitX", datetime(1925, 6, 15))
    assert unit is None  # No unit should be found
    assert unit_state is None  # No unit state should be found
    assert timespan is None  # No timespan should be found

# Test for create_next_unit_state method
def test_create_next_unit_state():
    unit, _ = create_test_units()
    registry = UnitRegistry(unit_list=[unit])
    
    # Test: create the next state for the unit starting from 1931-01-01
    old_state, new_state = registry.create_next_unit_state("unitA", datetime(1932, 1, 1))
    
    assert old_state == unit.states[-2]
    assert old_state.current_name == "District B"  # The name should match the previous state
    assert old_state.timespan.start == datetime(1930, 1, 1)  # The start should be held unchanged 
    assert old_state.timespan.end == datetime(1932, 1, 1)  # The end date should match the date passed
    
    assert new_state == unit.states[-1]
    assert new_state.current_name == "District B"  # The name should match the previous state
    assert new_state.timespan.start == datetime(1932, 1, 1)  # The start of the new state should match the date passed
    assert new_state.timespan.end == datetime(1938, 1, 1)  # The end date should match the start date for now
    
    assert len(unit.states) == 3  # The unit should now have 3 states

    # Test: Appropriate error is raised if unit_name is not found in the registry
    with pytest.raises(ValueError, match="Invalid unit_name: unitC"):
        registry.create_next_unit_state("unitC", datetime(1930, 1, 1))

    # Test: Appropriate error is raised if no state exists that covers the given date
    with pytest.raises(ValueError, match="Invalid date: 1922-01-01"):
        registry.create_next_unit_state("unitA", datetime(1922, 1, 1))

# Test for all_unit_states_by_date method
def test_all_unit_states_by_date():
    unit1, unit2 = create_test_units()
    state1 = unit1.states[0]
    state2 = unit1.states[1]
    state3 = unit2.states[0]
    registry = UnitRegistry(unit_list=[unit1, unit2])
    assert registry.all_unit_states_by_date(datetime(1927,1,1)) == [(unit1, state1), (unit2, state3)]
    assert registry.all_unit_states_by_date(datetime(1933,1,1)) == [(unit1, state2)]


############################################################################
#                            Region class tests                            #
############################################################################

def test_dist_state_creation():
    timespan = TimeSpan(start=datetime(1925, 1, 1), end=datetime(1930, 12, 31))
    state = DistState(
        current_name="District X",
        current_seat_name="Seat X",
        current_dist_type="w",
        timespan=timespan,
        current_territory=None
    )

    assert state.current_name == "District X"
    assert state.current_dist_type == "w"
    assert state.timespan.start == datetime(1925, 1, 1)

############################################################################
#                           District class tests                           #
############################################################################


def test_district_creation_and_state_validation():
    state = DistState(
        current_name="District X",
        current_seat_name="Seat X",
        current_dist_type="w",
        timespan=TimeSpan(start=datetime(1925, 1, 1), end=datetime(1930, 12, 31)),
        current_territory=None
    )

    district = District(
        name_id="dist_x",
        name_variants=["dist_x", "district_ex"],
        seat_name_variants=["seat_x"],
        states=[state]
    )

    assert district.name_id == "dist_x"
    assert isinstance(district.states[0], DistState)
    assert district.find_state_by_date(datetime(1926, 1, 1)) == state

############################################################################
#                        DistrictRegistry class tests                      #
############################################################################

def test_dist_registry_add_unit_success():
    registry = DistrictRegistry(unit_list=[])

    district_data = {
        "name_id": "dist1",
        "name_variants": ["dist1", "district one"],
        "seat_name_variants": ["seat1"],
        "states": [
            {
                "current_name": "District One",
                "current_seat_name": "Seat One",
                "current_dist_type": "w",
                "current_territory": None,
                "timespan": {
                    "start": "1923-01-01T00:00:00",
                    "end": "1930-12-31T00:00:00"
                }
            }
        ]
    }

    added = registry.add_unit(district_data)
    assert isinstance(added, District)
    assert added.name_id == "dist1"
    assert len(registry.unit_list) == 1

############################################################################
#                          RegionState class tests                         #
############################################################################

def test_region_state_creation():
    state = RegionState(
        current_name="Region A",
        current_seat_name="Capital A",
        timespan=TimeSpan(start=datetime(1926, 1, 1), end=datetime(1935, 12, 31))
    )

    assert state.current_name == "Region A"

############################################################################
#                            Region class tests                            #
############################################################################


def test_region_creation():
    state = RegionState(
        current_name="Region A",
        current_seat_name="Capital A",
        timespan=TimeSpan(start=datetime(1926, 1, 1), end=datetime(1935, 12, 31))
    )

    region = Region(
        name_id="reg_a",
        name_variants=["reg_a", "region_alpha"],
        seat_name_variants=["capital_a"],
        is_homeland=True,
        states=[state]
    )

    assert region.is_homeland
    assert isinstance(region.states[0], RegionState)

############################################################################
#                        RegionRegistry class tests                        #
############################################################################


def test_region_registry_add_unit_success():
    registry = RegionRegistry(unit_list=[])

    region_data = {
        "name_id": "reg1",
        "name_variants": ["reg1", "region one"],
        "seat_name_variants": ["seatR"],
        "is_homeland": True,
        "states": [
            {
                "current_name": "Region One",
                "current_seat_name": "Seat One",
                "current_dist_type": "m",
                "timespan": {
                    "start": "1923-01-01T00:00:00",
                    "end": "1930-12-31T00:00:00"
                }
            }
        ]
    }

    added = registry.add_unit(region_data)
    assert isinstance(added, Region)
    assert added.name_id == "reg1"
    assert len(registry.unit_list) == 1


def test_region_registry_rejects_district_instance():
    registry = RegionRegistry(unit_list=[])

    district_data = {
        "name_id": "dist_wrong",
        "name_variants": ["dist_wrong", "wrong district"],
        "seat_name_variants": ["seatX"],
        "states": [
            {
                "current_name": "District X",
                "current_seat_name": "Seat X",
                "current_dist_type": "w",
                "current_territory": None,
                "timespan": {
                    "start": "1923-01-01T00:00:00",
                    "end": "1930-12-31T00:00:00"
                }
            }
        ]
    }

    with pytest.raises(Exception):
        # This should fail because the data does not conform to Region
        registry.add_unit(district_data)
