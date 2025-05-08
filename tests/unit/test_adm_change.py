import pytest
from datetime import datetime
from pydantic import ValidationError
from io import StringIO
from unittest.mock import patch

from ...data_models.adm_timespan import TimeSpan
from ...data_models.adm_state import AdministrativeState
from ...data_models.adm_unit import *
from ...data_models.adm_change import *

# ---------------------------------------------------------------------------- #
#                       Fixtures for Change class testing                      #
# ---------------------------------------------------------------------------- #

############################################################################
#                           UnitReform class tests                        #
############################################################################

# Test cases related to the UnitReform class.

# ─── FIXTURES FOR VALID CASES ──────────────────────────────────────────────────

# Fixtures region_reform_matter_fixture and district_reform_matter_fixture are defined in the conftest.py file.

# ─── TESTS USING FIXTURES ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "unit_type, current_name, to_reform_seat_name, should_raise",
    [
        ("Region", "region_a", "seat_region_a", False),
        ("Region", "wrong_region", "seat_region_a", False),
        ("Region", "region_a", "wrong_seat", False),
        ("Region", "wrong_region", "wrong_seat", False),
        ("District", "district_a", "seat_a", False),
        ("District", "wrong_district", "seat_a", False),
        ("District", "district_a", "wrong_seat", False),
        ("District", "wrong_district", "wrong_seat", False),
    ]
)
def test_unit_reform_construction_valid(
    unit_type,
    current_name,
    to_reform_seat_name,
    should_raise,
    parametrized_region_reform_matter
):
    reform = parametrized_region_reform_matter(unit_type, current_name, to_reform_seat_name)

    assert reform.unit_type == unit_type
    assert reform.current_name == current_name
    assert reform.to_reform == {
        "current_name": unit_type.lower() + "_a",
        "current_seat_name": to_reform_seat_name
    }
    assert reform.after_reform == {
        "current_name": f"{unit_type.lower()}_a_Reformed",
        "current_seat_name": "seat_a_Reformed"
    }

# ─── INVALID CONSTRUCTION TESTS ────────────────────────────────────────────────

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


###########################################################################
# UnitReform.echo() method tests

# Test for Polish language and Region reform
def test_echo_pol_region(region_reform_matter_fixture):
    # I use patch to temporarily replace sys.stdout (where print normally writes to the console)
    # with a StringIO object, so that we can capture the output printed by the echo method.
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        # Now call the 'echo' method on the region reform object.
        # This will trigger the print statements inside echo, but instead of printing to the console,
        # the output will be captured by the StringIO object (fake_out).
        region_reform_matter_fixture.echo(date=datetime(1927,4,30), source="Test Source", lang="pol")
        
        # After the echo method runs, I can get the captured output from StringIO using getvalue().
        # This will return the exact string that was "printed" by the echo method.
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 dokonano reformy województwa region_a. "
            "Przed reformą: dict_items([('current_name', 'region_a'), ('current_seat_name', 'seat_region_a')]) "
            "vs po reformie: dict_items([('current_name', 'region_a_Reformed'), ('current_seat_name', 'seat_a_Reformed')]) "
            "(Test Source).")
        # Assert that the captured output is exactly what we expect.
        assert printed_output == expected_output

# Test for English language and Region reform
def test_echo_eng_region(region_reform_matter_fixture):
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        region_reform_matter_fixture.echo(date=datetime(1927,4,30), source="Test Source", lang="eng")
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 region region_a was reformed. "
            "Before the reform: dict_items([('current_name', 'region_a'), ('current_seat_name', 'seat_region_a')]) "
            "vs after the reform: dict_items([('current_name', 'region_a_Reformed'), ('current_seat_name', 'seat_a_Reformed')]) "
            "(Test Source).")
        assert printed_output == expected_output

# Test for Polish language and District reform
def test_echo_pol_district(district_reform_matter_fixture):
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        district_reform_matter_fixture.echo(date=datetime(1927,4,30), source="Test Source", lang="pol")
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 dokonano reformy powiatu district_a. "
            "Przed reformą: dict_items([('current_dist_type', 'w'), ('current_name', 'district_a'), ('current_seat_name', 'seat_a')]) "
            "vs po reformie: dict_items([('current_dist_type', 'm'), ('current_name', 'district_a_Reformed'), ('current_seat_name', 'seat_a_Reformed')]) "
            "(Test Source).")
        assert printed_output == expected_output

# Test for English language and District reform
def test_echo_eng_district(district_reform_matter_fixture):
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        district_reform_matter_fixture.echo(date=datetime(1927,4,30), source="Test Source", lang="eng")
        printed_output = mock_stdout.getvalue().strip()
        expected_output = (
            "1927-04-30 district district_a was reformed. "
            "Before the reform: dict_items([('current_dist_type', 'w'), ('current_name', 'district_a'), ('current_seat_name', 'seat_a')]) "
            "vs after the reform: dict_items([('current_dist_type', 'm'), ('current_name', 'district_a_Reformed'), ('current_seat_name', 'seat_a_Reformed')]) "
            "(Test Source).")
        assert printed_output == expected_output

############################################################################
#                           OneToMany class tests                          #
############################################################################

# ─── FIXTURES FOR VALID CASES ──────────────────────────────────────────────────

# Fixtures one_to_many_take_to_create_true_fixture, one_to_many_take_to_create_false_fixture,
# and one_to_many_matter_fixture are defined in the conftest.py file.

# ─── TESTS USING FIXTURES ──────────────────────────────────────────────────────

def test_take_to_create_true_valid(one_to_many_take_to_create_true_fixture):
    take_to = one_to_many_take_to_create_true_fixture
    assert take_to.create is True
    assert take_to.district.name_id == "district_x"
    assert take_to.new_district_address is not None

def test_take_to_create_false_valid(one_to_many_take_to_create_false_fixture):
    take_to = one_to_many_take_to_create_false_fixture
    assert take_to.create is False
    assert take_to.current_name == "district_b"

def test_valid_one_to_many_change(one_to_many_matter_fixture):
    change = one_to_many_matter_fixture
    assert change.change_type == "OneToMany"
    assert change.unit_attribute == "territory"
    assert change.take_from.current_name == "district_a"
    assert len(change.take_to) == 2
    assert any(t.create for t in change.take_to)
    assert any(not t.create for t in change.take_to)

# ─── INVALID CONSTRUCTION TESTS ────────────────────────────────────────────────

def test_take_to_create_true_missing_district():
    with pytest.raises(ValidationError) as exc_info:
        OneToManyTakeTo(
            create=True,
            current_name="district_x",
            # missing district
            new_district_address = ('HOMELAND', 'region_a', 'district_x')
        )
    assert "must be passed as 'district' attribute" in str(exc_info.value)

def test_take_to_create_true_missing_address(change_test_setup):
    with pytest.raises(ValidationError) as exc_info:
        OneToManyTakeTo(
            create=True,
            current_name="district_x",
            district=change_test_setup["district_x"],
        )
    assert "must be passed as 'new_district_address' attribute" in str(exc_info.value)

def test_take_to_create_false_missing_name():
    with pytest.raises(ValidationError) as exc_info:
        OneToManyTakeTo(
            create=False,
            current_name="",
        )
    assert "must be passed as 'name_id' attribute" in str(exc_info.value)


############################################################################
#                           ManyToOne class tests                        #
############################################################################

# Test cases related to the ManyToOne class.

# ─── VALID FIXTURES ─────────────────────────────────────────────────────────────

# Fixtures create_many_to_one_matter_fixture and reuse_many_to_one_matter_fixture are defined in the conftest.py file.

# ─── VALIDATION TESTS FOR CONSTRUCTION ─────────────────────────────────────────

def test_many_to_one_create_fixture_valid(create_many_to_one_matter_fixture):
    change = create_many_to_one_matter_fixture
    assert change.change_type == "ManyToOne"
    assert change.take_to.create is True
    assert change.take_to.district.name_id == "district_x"
    assert len(change.take_from) == 2
    assert all(isinstance(f, ManyToOneTakeFrom) for f in change.take_from)


def test_many_to_one_reuse_fixture_valid(reuse_many_to_one_matter_fixture):
    change = reuse_many_to_one_matter_fixture
    assert change.take_to.create is False
    assert change.take_to.current_name == "district_e"
    assert all(isinstance(f, ManyToOneTakeFrom) for f in change.take_from)
    assert len(change.take_from) == 2

# ─── INVALID CONSTRUCTION TESTS ────────────────────────────────────────────────

def test_many_to_one_missing_district_on_create():
    with pytest.raises(ValueError, match="must be passed as 'district' attribute when 'create' is True"):
        ManyToOneTakeTo(
            create=True,
            current_name="district_x",
            district=None,
            new_district_address = ('HOMELAND', 'region_a', 'district_x')
        )
    
def test_many_to_one_missing_address_on_create(change_test_setup):
    with pytest.raises(ValueError, match="must be passed as 'new_district_address' attribute"):
        ManyToOneTakeTo(
            create=True,
            current_name="district_x",
            district=change_test_setup["district_x"]
            # Missing address
        )

def test_many_to_one_missing_name_on_reuse():
    with pytest.raises(ValueError, match="must be passed as 'name_id' attribute when 'create' is False"):
        ManyToOneTakeTo(
            create=False,
            current_name=None
        )


############################################################################
#                           ChangeAdmState class tests                    #
############################################################################

# Test cases related to the ChangeAdmState class.

# ─── VALID FIXTURES ─────────────────────────────────────────────────────────────

# Fixtures region_change_adm_state_matter_fixture and district_change_adm_state_matter_fixture
# are defined in the conftest.py file.

# ─── VALIDATION TESTS FOR CONSTRUCTION ─────────────────────────────────────────

def test_region_change_adm_state_matter_fixture_structure(region_change_adm_state_matter_fixture):
    change = region_change_adm_state_matter_fixture
    assert change.take_from == ("ABROAD", "region_c")
    assert change.take_to == ("HOMELAND", "region_c")
    assert len(change.take_from) == len(change.take_to) == 2
 

def test_district_change_adm_state_matter_fixture_structure(district_change_adm_state_matter_fixture):
    change = district_change_adm_state_matter_fixture
    assert change.take_from[2] == "district_a"
    assert change.take_to[2] == "district_a"
    assert len(change.take_from) == len(change.take_to) == 3

# ─── INVALID CONSTRUCTION TESTS ────────────────────────────────────────────────

def test_invalid_changeadmstate_mismatched_address_lengths():
    with pytest.raises(ValueError) as exc_info:
        ChangeAdmState(
            change_type="ChangeAdmState",
            take_from=("HOMELAND", "region_A"),
            take_to=("HOMELAND", "region_B", "district_c"),
        )
    assert "'take_from' and 'take_to' must be the same length" in str(exc_info.value)


############################################################################
#                           Change class tests                            #
############################################################################

# Test cases related to the Change class.

@pytest.mark.parametrize(
    ("fixture_name", "region_before", "region_after", "district_before", "district_after"),
    [
        ("region_reform_matter_fixture", ["region_a"], ["region_a_Reformed"], [], []),
        ("district_reform_matter_fixture", [], [], ["district_a"], ["district_a_Reformed"]),
        ("one_to_many_matter_fixture", [], [], ["district_a", "district_b"], ["district_b", "district_x"]),
        ("create_many_to_one_matter_fixture", [], [], ["district_a", "district_b"], ["district_b", "district_x"]),
        ("reuse_many_to_one_matter_fixture", [], [], ["district_c", "district_d", "district_e"], ["district_c", "district_e"]),
        ("region_change_adm_state_matter_fixture", ["region_c"], ["region_c"], [], []),
        ("district_change_adm_state_matter_fixture", ["region_a"], ["region_b"], ["district_a"], ["district_a"]),
    ]
)

def test_change_construction_from_matter_fixtures(
    request,
    fixture_name,
    region_before,
    region_after,
    district_before,
    district_after
):
    matter = request.getfixturevalue(fixture_name)

    change = Change(
        date=datetime(1930, 5, 1),
        source="Legal Act XYZ",
        description="Test change",
        order=1,
        matter=matter
    )

    assert isinstance(change, Change)
    assert change.date.year == 1930
    assert change.description == "Test change"
    assert change.matter == matter

    # Check the correctness of the 'units_affected' attribute definition.
    assert set(change.units_affected_current_names["Region"]["before"]) == set(region_before)
    assert set(change.units_affected_current_names["Region"]["after"]) == set(region_after)
    assert set(change.units_affected_current_names["District"]["before"]) == set(district_before)
    assert set(change.units_affected_current_names["District"]["after"]) == set(district_after)
