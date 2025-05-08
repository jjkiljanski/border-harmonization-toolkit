import pytest
from datetime import datetime
from ...data_models.adm_timespan import TimeSpan
import csv
import os

from ...data_models.adm_state import AdministrativeState, Address
from utils.exceptions import ConsistencyError

# --- TEST REGION CREATE_NEW --- #

def test_create_new(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    # Setup
    new_date = datetime(1931, 1, 1)

    # Execute
    new_state = sample_adm_state.create_new(new_date)

    # Validate original
    assert new_state.timespan.start == new_date
    assert sample_adm_state.timespan.end == new_date
    assert new_state != sample_adm_state
    assert sample_adm_state.timespan.start < sample_adm_state.timespan.middle < new_date
    assert new_date < new_state.timespan.middle < new_state.timespan.end
    assert new_state.unit_hierarchy == sample_adm_state.unit_hierarchy

# --- TEST REGION ADDRESS --- #

# Test for the all_region_names and all_district_names methods
def test_all_regions_districts_names(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    assert sample_adm_state.all_region_names() == ['region_a', 'region_b', 'region_c']
    assert sample_adm_state.all_district_names() == ['district_' + suffix for suffix in ['a', 'b', 'c', 'd', 'e', 'f']]

def test_pop_region_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_a")
    removed = sample_adm_state.pop_address(address)

    assert "HOMELAND" in sample_adm_state.unit_hierarchy
    assert "region_a" not in sample_adm_state.unit_hierarchy["HOMELAND"]
    assert "district_a" in removed  # Confirm content was returned

    assert sample_adm_state.all_region_names() == ['region_b', 'region_c']


def test_add_region_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address = ("HOMELAND",)
    new_region = {"region_x": {"district_y": {}}}
    sample_adm_state.add_address(address + ("region_x",), new_region["region_x"])

    assert "region_x" in sample_adm_state.unit_hierarchy["HOMELAND"]
    assert sample_adm_state.unit_hierarchy["HOMELAND"]["region_x"]=={"district_y": {}}

def test_get_region_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address_1 = ("HOMELAND","region_a")
    address_2 = ("HOMELAND", "region_x")

    assert sample_adm_state.get_address(address_1)
    assert not sample_adm_state.get_address(address_2)

def test_find_region_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    
    assert sample_adm_state.find_address("region_a", "Region") == ('HOMELAND', 'region_a')
    assert sample_adm_state.find_address("region_x", "Region") is None

def test_find_and_pop_region_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    
    removed = sample_adm_state.find_and_pop("region_a", "Region")
    assert "HOMELAND" in sample_adm_state.unit_hierarchy
    assert "region_a" not in sample_adm_state.unit_hierarchy["HOMELAND"]
    assert "district_a" in removed  # Confirm content was returned

    with pytest.raises(ValueError, match=r"doesn't exist"):
        sample_adm_state.find_and_pop("region_x", "Region")

# --- TEST VERIFY AND STANDARDIZE ADDRESS --- #

def test_verify_and_standardize_address(change_test_setup):
    adm_state = change_test_setup["administrative_state"]
    dist_registry = change_test_setup["dist_registry"]
    region_registry = change_test_setup["region_registry"]

    address_1 = ("HOMELAND", "region_a", "district_b")
    assert ("HOMELAND", "region_a", "district_b") == adm_state.verify_and_standardize_address(address_1, region_registry, dist_registry)

    address_2 = ("HOMELAND", "REGION_A", "district_b")
    assert ("HOMELAND", "region_a", "district_b") == adm_state.verify_and_standardize_address(address_2, region_registry, dist_registry)

    address_3 = ("HOMELAND", "region_a", "DISTRICT_B")
    assert ("HOMELAND", "region_a", "district_b") == adm_state.verify_and_standardize_address(address_3, region_registry, dist_registry)

    address_4 = ("HOMELAND", "region_a", "district_x")
    with pytest.raises(ConsistencyError, match=r"no district with name variant"):
        adm_state.verify_and_standardize_address(address_4, region_registry, dist_registry)
    
    address_5 = ("HOMELAND", "region_x", "district_a")
    with pytest.raises(ConsistencyError, match=r"no region with name variant"):
        adm_state.verify_and_standardize_address(address_5, region_registry, dist_registry)

    address_6 = ("HOMELAND", "region_a", "district_c")
    with pytest.raises(ConsistencyError, match=r"doesn't exist in the administrative state"):
        adm_state.verify_and_standardize_address(address_6, region_registry, dist_registry)
    
    address_7 = ("HOMELAND", "region_a", "district_b")
    dist_registry.find_unit('district_b').abolish(datetime(1922,1,1))
    with pytest.raises(ConsistencyError, match=r"no district state for district"):
        adm_state.verify_and_standardize_address(address_7, region_registry, dist_registry)

    address_8 = ("HOMELAND", "region_a", "district_a")
    region_registry.find_unit('region_a').abolish(datetime(1922,1,1))
    with pytest.raises(ConsistencyError, match=r"no region state for region"):
        adm_state.verify_and_standardize_address(address_8, region_registry, dist_registry)
    
    


# --- TEST DISTRICT ADDRESS --- #

def test_pop_district_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_a", "district_a")
    removed = sample_adm_state.pop_address(address)

    assert "district_a" not in sample_adm_state.unit_hierarchy["HOMELAND"]["region_a"]
    assert removed == {}


def test_add_district_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_b")
    new_district_name = "district_z"
    new_district_data = {}

    sample_adm_state.add_address(address + (new_district_name,), new_district_data)

    assert "district_z" in sample_adm_state.unit_hierarchy["HOMELAND"]["region_b"]
    assert sample_adm_state.unit_hierarchy["HOMELAND"]["region_b"]["district_z"] == {}

def test_get_district_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address_1 = ("HOMELAND","region_a", "district_b") # Existent address
    address_2 = ("HOMELAND", "region_b", "district_z") # Nonexistent address

    assert sample_adm_state.get_address(address_1)
    assert not sample_adm_state.get_address(address_2)

def test_find_district_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    
    assert sample_adm_state.find_address("district_b", "District") == ("HOMELAND","region_a", "district_b")
    assert sample_adm_state.find_address("district_z", "District") is None

def test_find_and_pop_district_address(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    
    removed = sample_adm_state.find_and_pop("district_b", "District")
    assert removed == {}
    assert "district_b" not in sample_adm_state.unit_hierarchy["HOMELAND"]["region_a"]

    with pytest.raises(ValueError, match=r"doesn't exist"):
        sample_adm_state.find_and_pop("district_z", "District")

# --- ERROR HANDLING --- #

def test_pop_nonexistent_address_raises(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_x", "district_i")  # Invalid region
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_adm_state.pop_address(address)

def test_add_nonexistent_path_raises(change_test_setup):
    sample_adm_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "NonExistentRegion", "NewDistrict")
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_adm_state.add_address(address, {})

# --- TESTS for the to_address_list method --- #

def test_to_address_list(change_test_setup):
    valid_adm_state = change_test_setup["administrative_state"]
    dist_registry = change_test_setup["dist_registry"]
    region_registry = change_test_setup["region_registry"]

    default_list = valid_adm_state.to_address_list()
    correct_default_list = [
        ("ABROAD", "region_c", "district_e"),
        ("ABROAD", "region_c", "district_f"),
        ("HOMELAND", "region_a", "district_a"),
        ("HOMELAND", "region_a", "district_b"),
        ("HOMELAND", "region_b", "district_c"),
        ("HOMELAND", "region_b", "district_d"),
    ]
    assert default_list == correct_default_list

    only_homeland_list = valid_adm_state.to_address_list(only_homeland = True, region_registry = region_registry, dist_registry = dist_registry)
    correct_only_homeland_list = [
        ("region_a", "district_a"),
        ("region_a", "district_b"),
        ("region_b", "district_c"),
        ("region_b", "district_d"),
    ]
    assert only_homeland_list == correct_only_homeland_list

    with_variants_list = valid_adm_state.to_address_list(with_variants = True, region_registry = region_registry, dist_registry = dist_registry)
    correct_with_variants_list = [
        ('ABROAD', 'region_c', 'district_e'),
        ('ABROAD', 'region_c', 'DISTRICT_E'),
        ('ABROAD', 'REGION_C', 'district_e'),
        ('ABROAD', 'REGION_C', 'DISTRICT_E'),

        ('ABROAD', 'region_c', 'district_f'),
        ('ABROAD', 'region_c', 'DISTRICT_F'),
        ('ABROAD', 'REGION_C', 'district_f'),
        ('ABROAD', 'REGION_C', 'DISTRICT_F'),

        ('HOMELAND', 'region_a', 'district_a'),
        ('HOMELAND', 'region_a', 'DISTRICT_A'),
        ('HOMELAND', 'REGION_A', 'district_a'),
        ('HOMELAND', 'REGION_A', 'DISTRICT_A'),

        ('HOMELAND', 'region_a', 'district_b'),
        ('HOMELAND', 'region_a', 'DISTRICT_B'),
        ('HOMELAND', 'REGION_A', 'district_b'),
        ('HOMELAND', 'REGION_A', 'DISTRICT_B'),

        ('HOMELAND', 'region_b', 'district_c'),
        ('HOMELAND', 'region_b', 'DISTRICT_C'),
        ('HOMELAND', 'REGION_B', 'district_c'),
        ('HOMELAND', 'REGION_B', 'DISTRICT_C'),

        ('HOMELAND', 'region_b', 'district_d'),
        ('HOMELAND', 'region_b', 'DISTRICT_D'),
        ('HOMELAND', 'REGION_B', 'district_d'),
        ('HOMELAND', 'REGION_B', 'DISTRICT_D'),
    ]
    correct_with_variants_list.sort()

    assert with_variants_list == correct_with_variants_list

    region_a, region_a_state, _ = region_registry.find_unit_state_by_date('region_a', datetime(1930,1,1))
    region_a_state.current_name = 'REGION_A'
    district_a, district_a_state, _ = dist_registry.find_unit_state_by_date('district_c', datetime(1930,1,1))
    district_a_state.current_name = 'DISTRICT_C'

    normal_names_id_list = valid_adm_state.to_address_list()
    correct_normal_names_id_list = [
        ("ABROAD", "region_c", "district_e"),
        ("ABROAD", "region_c", "district_f"),
        ("HOMELAND", "region_a", "district_a"),
        ("HOMELAND", "region_a", "district_b"),
        ("HOMELAND", "region_b", "district_c"),
        ("HOMELAND", "region_b", "district_d"),
    ]
    assert normal_names_id_list == correct_normal_names_id_list

    current_names_list = valid_adm_state.to_address_list(current_not_id = True, region_registry = region_registry, dist_registry = dist_registry)
    correct_current_names_list = [
        ("ABROAD", "region_c", "district_e"),
        ("ABROAD", "region_c", "district_f"),
        ("HOMELAND", "REGION_A", "district_a"),
        ("HOMELAND", "REGION_A", "district_b"),
        ("HOMELAND", "region_b", "DISTRICT_C"),
        ("HOMELAND", "region_b", "district_d"),
    ]
    assert current_names_list == correct_current_names_list

# --- TESTS for the to_csv method --- #

def test_to_csv_outputs_correct_data(change_test_setup, tmp_path):
    sample_adm_state = change_test_setup["administrative_state"]
    # Arrange
    csv_file = tmp_path / "output.csv"

    try:
        # Act
        sample_adm_state.to_csv(csv_file)

        # Assert: File was created
        assert csv_file.exists()

        # Read CSV content
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            rows = list(reader)

        # All rows must be pairs
        assert all(len(row) == 2 for row in rows)

        # Unpack first and second elements from each pair
        first_elements = [row[0] for row in rows]
        second_elements = [row[1] for row in rows]
        pairs = [(row[0], row[1]) for row in rows]

        # Check specific conditions
        assert "region_a" in first_elements
        assert "district_c" in second_elements
        assert ("region_a", "district_b") in pairs
        assert ("region_a", "district_c") not in pairs

    finally:
        # Cleanup: delete the file if it exists
        if csv_file.exists():
            csv_file.unlink()



