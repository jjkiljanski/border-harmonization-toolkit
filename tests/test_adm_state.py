import pytest
from datetime import datetime
from border_harmonization_toolkit.data_models.adm_timespan import TimeSpan
from border_harmonization_toolkit.data_models.adm_state import AdministrativeState

# Sample base hierarchy for tests
@pytest.fixture
def sample_admin_state():
    return AdministrativeState(
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1933, 1, 1)),
        unit_hierarchy={
            "Poland": {
                "RegionA": {
                    "District1": {"some": "data"},
                    "District2": {"other": "info"},
                },
                "RegionB": {
                    "District3": {"some": "more"},
                }
            },
            "Abroad": {
                "RegionX": {
                    "DistrictZ": {"zdata": "zval"}
                }
            }
        }
    )

# --- TEST REGION ADDRESS --- #

def test_pop_region_address(sample_admin_state):
    address = ("Poland", "RegionA")
    removed = sample_admin_state.pop_address(address)

    assert "RegionA" not in sample_admin_state.unit_hierarchy["Poland"]
    assert "District1" in removed  # Confirm content was returned


def test_add_region_address(sample_admin_state):
    address = ("Poland",)
    new_region = {"RegionC": {"DistrictX": {"foo": "bar"}}}
    sample_admin_state.add_address(address + ("RegionC",), new_region["RegionC"])

    assert "RegionC" in sample_admin_state.unit_hierarchy["Poland"]
    assert sample_admin_state.unit_hierarchy["Poland"]["RegionC"]["DistrictX"]["foo"] == "bar"

# --- TEST DISTRICT ADDRESS --- #

def test_pop_district_address(sample_admin_state):
    address = ("Poland", "RegionA", "District1")
    removed = sample_admin_state.pop_address(address)

    assert "District1" not in sample_admin_state.unit_hierarchy["Poland"]["RegionA"]
    assert removed == {"some": "data"}


def test_add_district_address(sample_admin_state):
    address = ("Poland", "RegionB")
    new_district_name = "District4"
    new_district_data = {"info": "new district"}

    sample_admin_state.add_address(address + (new_district_name,), new_district_data)

    assert "District4" in sample_admin_state.unit_hierarchy["Poland"]["RegionB"]
    assert sample_admin_state.unit_hierarchy["Poland"]["RegionB"]["District4"]["info"] == "new district"

# --- ERROR HANDLING --- #

def test_pop_nonexistent_address_raises(sample_admin_state):
    address = ("Poland", "RegionX", "District9")  # Invalid region
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_admin_state.pop_address(address)

def test_add_nonexistent_path_raises(sample_admin_state):
    address = ("Poland", "NonExistentRegion", "NewDistrict")
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_admin_state.add_address(address, {"any": "thing"})
