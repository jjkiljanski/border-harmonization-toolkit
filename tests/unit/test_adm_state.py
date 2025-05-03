import pytest
from datetime import datetime
from ...data_models.adm_timespan import TimeSpan
from ...data_models.adm_state import AdministrativeState

# Sample base hierarchy for tests
@pytest.fixture
def sample_admin_state():
    return AdministrativeState(
        timespan=TimeSpan(start=datetime(1923, 1, 1), end=datetime(1933, 1, 1)),
        unit_hierarchy={
            "HOMELAND": {
                "region_a": {
                    "district_a": {"some": "data"},
                    "district_b": {"other": "info"},
                },
                "region_b": {
                    "district_c": {"some": "more"},
                }
            },
            "ABROAD": {
                "region_x": {
                    "district_z": {"zdata": "zval"}
                }
            }
        }
    )

# --- TEST REGION ADDRESS --- #

def test_pop_region_address(sample_admin_state):
    address = ("HOMELAND", "region_a")
    removed = sample_admin_state.pop_address(address)

    assert "HOMELAND" not in sample_admin_state.unit_hierarchy["HOMELAND"]
    assert "district_a" in removed  # Confirm content was returned


def test_add_region_address(sample_admin_state):
    address = ("HOMELAND",)
    new_region = {"region_c": {"district_x": {"foo": "bar"}}}
    sample_admin_state.add_address(address + ("region_c",), new_region["region_c"])

    assert "region_c" in sample_admin_state.unit_hierarchy["HOMELAND"]
    assert sample_admin_state.unit_hierarchy["HOMELAND"]["region_c"]["district_x"]["foo"] == "bar"

def test_get_region_address(sample_admin_state):
    address_1 = ("HOMELAND","region_a")
    address_2 = ("HOMELAND", "region_x")

    assert sample_admin_state.get_address(address_1)
    assert not sample_admin_state.get_address(address_2)

# --- TEST DISTRICT ADDRESS --- #

def test_pop_district_address(sample_admin_state):
    address = ("HOMELAND", "region_a", "district_a")
    removed = sample_admin_state.pop_address(address)

    assert "district_a" not in sample_admin_state.unit_hierarchy["HOMELAND"]["region_a"]
    assert removed == {"some": "data"}


def test_add_district_address(sample_admin_state):
    address = ("HOMELAND", "region_b")
    new_district_name = "district_d"
    new_district_data = {"info": "new district"}

    sample_admin_state.add_address(address + (new_district_name,), new_district_data)

    assert "district_d" in sample_admin_state.unit_hierarchy["HOMELAND"]["region_b"]
    assert sample_admin_state.unit_hierarchy["HOMELAND"]["region_b"]["district_d"]["info"] == "new district"

def test_get_district_address(sample_admin_state):
    address_1 = ("HOMELAND","region_a", "district_b") # Existent address
    address_2 = ("HOMELAND", "region_b", "district_d") # Nonexistent address

    assert sample_admin_state.get_address(address_1)
    assert not sample_admin_state.get_address(address_2)

# --- ERROR HANDLING --- #

def test_pop_nonexistent_address_raises(sample_admin_state):
    address = ("HOMELAND", "region_x", "district_i")  # Invalid region
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_admin_state.pop_address(address)

def test_add_nonexistent_path_raises(sample_admin_state):
    address = ("HOMELAND", "NonExistentRegion", "NewDistrict")
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_admin_state.add_address(address, {"any": "thing"})
