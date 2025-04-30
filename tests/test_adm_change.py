import pytest
from datetime import datetime
from pydantic import ValidationError
from io import StringIO
from unittest.mock import patch

from border_harmonization_toolkit.data_models.adm_timespan import TimeSpan
from border_harmonization_toolkit.data_models.adm_state import AdministrativeState
from border_harmonization_toolkit.data_models.adm_unit import *
from border_harmonization_toolkit.data_models.adm_change import *

@pytest.fixture
def change_test_setup():
    # Common timespan
    timespan = TimeSpan(start=datetime(1921, 2, 19), end=datetime(1938, 11, 16))

    # Create districts
    district_registry = DistrictRegistry(unit_list=[])
    for suffix in ['a', 'b', 'c', 'd', 'e', 'f']:
        name_id = f"district_{suffix}"
        district_registry.add_unit({
            "name_id": name_id,
            "name_variants": [name_id, name_id.upper()],
            "seat_name_variants": [f"seat_{suffix}", f"SEAT_{suffix}"],
            "states": [
                DistState(
                    current_name=name_id,
                    current_seat_name=f"seat_{suffix}",
                    current_dist_type="w",
                    timespan=timespan,
                    current_territory=None
                )
            ]
        })

    # Create regions
    region_registry = RegionRegistry(unit_list=[])
    for suffix in ['A', 'B', 'C']:
        region_registry.add_unit({
            "name_id": f"region_{suffix.lower()}",
            "name_variants": [f"region_{suffix.lower()}", f"REGION_{suffix}"],
            "seat_name_variants": [f"seat_region_{suffix.lower()}"],
            "states": [
                RegionState(
                    current_name=f"region_{suffix.lower()}",
                    current_seat_name=f"seat_region_{suffix.lower()}",
                    current_dist_type="m",
                    timespan=timespan
                )
            ],
            "is_homeland": suffix in ['A', 'B']
        })

    # Create administrative state
    unit_hierarchy = {
        "HOMELAND": {
            "region_a": {
                "district_a": {},
                "district_b": {}
            },
            "region_b": {
                "district_c": {},
                "district_d": {}
            }
        },
        "ABROAD": {
            "region_c": {
                "district_e": {},
                "district_f": {}
            }
        }
    }

    administrative_state = AdministrativeState(
        timespan=timespan,
        unit_hierarchy=unit_hierarchy
    )

    def district_x_to_create():
        return District(
            name_id="district_x",
            name_variants=["district_x", "DISTRICT_X"],
            seat_name_variants=["seat_x", "SEAT_X"],
            states=[
                DistState(
                    current_name="district_x",
                    current_seat_name="seat_x",
                    current_dist_type="w",
                    current_territory=None,
                    timespan=TimeSpan(start=datetime(1921, 2, 19), end=datetime(1938, 11, 16))
                )
            ]
        )

    return {
        "district_registry": district_registry,
        "region_registry": region_registry,
        "administrative_state": administrative_state,
        "district_x": district_x_to_create()
    }

############################################################################
#                           UnitReform class tests                        #
############################################################################

def test_unit_reform_valid():
    # Valid UnitReform
    reform = UnitReform(
        change_type = "UnitReform",
        unit_type="Region",
        current_name="region_A",
        to_reform={"current_name": "region_A", "current_seat_name": "seat_A"},
        after_reform={"current_name": "region_A_Reformed", "current_seat_name": "seat_A_Reformed"}
    )

    assert reform.unit_type == "Region"
    assert reform.current_name == "region_A"
    assert reform.to_reform == {"current_name": "region_A", "current_seat_name": "seat_A"}
    assert reform.after_reform == {"current_name": "region_A_Reformed", "current_seat_name": "seat_A_Reformed"}


def test_unit_reform_invalid_to_reform_type():
    # Invalid type for `to_reform` (should be a dictionary)
    with pytest.raises(TypeError, match="Both 'to_reform' and 'after_reform' must be dictionaries"):
        UnitReform(
            change_type = "UnitReform",
            unit_type="Region",
            current_name="region_A",
            to_reform="invalid_value",  # Invalid type
            after_reform={"current_name": "region_A_Reformed", "current_seat_name": "seat_A_Reformed"}
        )


def test_unit_reform_invalid_after_reform_type():
    # Invalid type for `after_reform` (should be a dictionary)
    with pytest.raises(TypeError, match="Both 'to_reform' and 'after_reform' must be dictionaries"):
        UnitReform(
            change_type = "UnitReform",
            unit_type="Region",
            current_name="region_A",
            to_reform={"current_name": "region_A", "current_seat_name": "seat_A"},
            after_reform="invalid_value"  # Invalid type
        )


def test_unit_reform_keys_mismatch():
    # Mismatched keys between `to_reform` and `after_reform`
    with pytest.raises(ValueError, match="`to_reform` and `after_reform` must have the same keys"):
        UnitReform(
            change_type = "UnitReform",
            unit_type="Region",
            current_name="region_A",
            to_reform={"current_name": "region_A", "current_seat_name": "seat_A"},
            after_reform={"current_name": "region_A_Reformed"}  # Mismatched key
        )
        
def test_unit_reform_valid_seat_name_change():
    # Valid reform where only seat name is changed
    reform = UnitReform(
        change_type = "UnitReform",
        unit_type="Region",
        current_name="region_A",
        to_reform={"current_seat_name": "seat_A"},
        after_reform={"current_seat_name": "seat_A_Reformed"}
    )

    assert reform.to_reform["current_seat_name"] == "seat_A"
    assert reform.after_reform["current_seat_name"] == "seat_A_Reformed"


def test_unit_reform_invalid_seat_name_change():
    # Invalid reform where current_seat_name is missing from to_reform
    with pytest.raises(ValueError, match="`to_reform` and `after_reform` must have the same keys"):
        UnitReform(
            change_type = "UnitReform",
            unit_type="Region",
            current_name="region_A",
            to_reform={"current_name": "region_A"},
            after_reform={"current_seat_name": "seat_A_Reformed"}
        )

def test_district_reform_valid(district_reform_matter):
    # Test for valid district reform
    reform = district_reform_matter
    
    assert reform.unit_type == "District"
    assert reform.current_name == "district_a"
    assert reform.to_reform == {"current_dist_type": "w", "current_name": "district_a", "current_seat_name": "seat_a"}
    assert reform.after_reform == {"current_dist_type": "m", "current_name": "district_a_Reformed", "current_seat_name": "seat_a_Reformed"}


def test_district_reform_valid_seat_name_change():
    # Valid district reform where only the seat name is changed
    reform = UnitReform(
        change_type = "UnitReform",
        unit_type="District",
        current_name="district_a",
        to_reform={"current_seat_name": "seat_A"},
        after_reform={"current_seat_name": "seat_A_Reformed"}
    )

    assert reform.to_reform["current_seat_name"] == "seat_A"
    assert reform.after_reform["current_seat_name"] == "seat_A_Reformed"


def test_district_reform_missing_current_name():
    # Missing current_name field in to_reform or after_reform
    with pytest.raises(ValueError, match="`to_reform` and `after_reform` must have the same keys"):
        UnitReform(
            change_type = "UnitReform",
            unit_type="District",
            current_name="district_a",
            to_reform={"current_dist_type": "w", "current_seat_name": "seat_A"},
            after_reform={"current_dist_type": "m", "current_name": "district_a_Reformed"}
        )

@pytest.fixture
def region_reform_matter():
    # Setup a UnitReform instance for Region reform
    return UnitReform(
        change_type = "UnitReform",
        unit_type="Region",
        current_name="region_a",
        to_reform={"current_name": "region_a", "current_seat_name": "seat_region_a"},
        after_reform={"current_name": "region_a_Reformed", "current_seat_name": "seat_region_a_Reformed"}
    )

@pytest.fixture
def district_reform_matter():
    # Setup a UnitReform instance for District reform
    return UnitReform(
        change_type = "UnitReform",
        unit_type="District",
        current_name="district_a",
        to_reform={"current_dist_type": "w", "current_name": "district_a", "current_seat_name": "seat_a"},
        after_reform={"current_dist_type": "m", "current_name": "district_a_Reformed", "current_seat_name": "seat_a_Reformed"}
    )


###########################################################################
# UnitReform.echo() method tests

# Test for Polish language and Region reform
def test_echo_pol_region(region_reform_matter):
    # I use patch to temporarily replace sys.stdout (where print normally writes to the console)
    # with a StringIO object, so that we can capture the output printed by the echo method.
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        # Now call the 'echo' method on the region reform object.
        # This will trigger the print statements inside echo, but instead of printing to the console,
        # the output will be captured by the StringIO object (fake_out).
        region_reform_matter.echo(date=datetime(1927,4,30), source="Test Source", lang="pol")
        
        # After the echo method runs, I can get the captured output from StringIO using getvalue().
        # This will return the exact string that was "printed" by the echo method.
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 dokonano reformy województwa region_a. "
            "Przed reformą: dict_items([('current_name', 'region_a'), ('current_seat_name', 'seat_region_a')]) "
            "vs po reformie: dict_items([('current_name', 'region_a_Reformed'), ('current_seat_name', 'seat_region_a_Reformed')]) "
            "(Test Source).")
        # Assert that the captured output is exactly what we expect.
        assert printed_output == expected_output

# Test for English language and Region reform
def test_echo_eng_region(region_reform_matter):
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        region_reform_matter.echo(date=datetime(1927,4,30), source="Test Source", lang="eng")
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 region region_a was reformed. "
            "Before the reform: dict_items([('current_name', 'region_a'), ('current_seat_name', 'seat_region_a')]) "
            "vs after the reform: dict_items([('current_name', 'region_a_Reformed'), ('current_seat_name', 'seat_region_a_Reformed')]) "
            "(Test Source).")
        assert printed_output == expected_output

# Test for Polish language and District reform
def test_echo_pol_district(district_reform_matter):
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        district_reform_matter.echo(date=datetime(1927,4,30), source="Test Source", lang="pol")
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 dokonano reformy powiatu district_a. "
            "Przed reformą: dict_items([('current_dist_type', 'w'), ('current_name', 'district_a'), ('current_seat_name', 'seat_a')]) "
            "vs po reformie: dict_items([('current_dist_type', 'm'), ('current_name', 'district_a_Reformed'), ('current_seat_name', 'seat_a_Reformed')]) "
            "(Test Source).")
        assert printed_output == expected_output

# Test for English language and District reform
def test_echo_eng_district(district_reform_matter):
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        district_reform_matter.echo(date=datetime(1927,4,30), source="Test Source", lang="eng")
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 district district_a was reformed. "
            "Before the reform: dict_items([('current_dist_type', 'w'), ('current_name', 'district_a'), ('current_seat_name', 'seat_a')]) "
            "vs after the reform: dict_items([('current_dist_type', 'm'), ('current_name', 'district_a_Reformed'), ('current_seat_name', 'seat_a_Reformed')]) "
            "(Test Source).")
        assert printed_output == expected_output


# Test cases related to the UnitReform class.

############################################################################
#                           OneToMany class tests                        #
############################################################################

def test_take_to_create_true_valid(change_test_setup):
    district_x_to_create = change_test_setup["district_x"]
    take_to = OneToManyTakeTo(
        create=True,
        current_name="district_x",
        district=district_x_to_create
    )
    assert take_to.create is True
    assert take_to.district.name_id == "district_x"

def test_take_to_create_true_missing_district():
    with pytest.raises(ValidationError) as exc_info:
        OneToManyTakeTo(
            create=True,
            current_name="district_x"
            # missing district
        )
    assert "must be passed as 'district' attribute" in str(exc_info.value)

def test_take_to_create_false_valid():
    take_to = OneToManyTakeTo(
        create=False,
        current_name="district_b"
    )
    assert take_to.create is False
    assert take_to.current_name == "district_b"

def test_take_to_create_false_missing_name():
    with pytest.raises(ValidationError) as exc_info:
        OneToManyTakeTo(
            create=False,
            current_name="",
        )
    assert "must be passed as 'name_id' attribute" in str(exc_info.value)

def test_valid_one_to_many_change(change_test_setup):
    district_x_to_create = change_test_setup["district_x"]
    change = OneToMany(
        change_type="OneToMany",
        unit_attribute="territory",
        unit_type="District",
        take_from=OneToManyTakeFrom(current_name="district_a", delete_unit=True),
        take_to=[
            OneToManyTakeTo(create=False, current_name="district_b", weight_from=0.3),
            OneToManyTakeTo(create=True, current_name="district_x", district=district_x_to_create, weight_from=0.7)
        ]
    )
    assert change.change_type == "OneToMany"
    assert change.unit_attribute == "territory"
    assert change.take_from.current_name == "district_a"
    assert len(change.take_to) == 2

@pytest.fixture
def one_to_many_change_fixture(change_test_setup):
    return OneToMany(
        change_type="OneToMany",
        unit_attribute="territory",
        unit_type="District",
        take_from=OneToManyTakeFrom(current_name="district_a", delete_unit=True),
        take_to=[
            OneToManyTakeTo(create=False, current_name="district_b", weight_from=0.5),
            OneToManyTakeTo(create=True, current_name="district_x", district=change_test_setup["district_x"], weight_from=0.5)
        ]
    )

# Test cases related to the OneToMany class.

############################################################################
#                           ManyToOne class tests                        #
############################################################################

# Test cases related to the ManyToOne class.

############################################################################
#                           ChangeAdmState class tests                    #
############################################################################

# Test cases related to the ChangeAdmState class.

############################################################################
#                           Change class tests                            #
############################################################################

# Test cases related to the Change class.
