import pytest
from datetime import datetime
from ...data_models.adm_timespan import TimeSpan
from ...data_models.adm_state import AdministrativeState
from copy import deepcopy

# --- TEST REGION ADDRESS --- #

# Test for the all_region_names and all_district_names methods
def test_all_regions_districts_names(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    assert sample_admin_state.all_region_names() == ['region_a', 'region_b', 'region_c']
    assert sample_admin_state.all_district_names() == ['district_' + suffix for suffix in ['a', 'b', 'c', 'd', 'e', 'f']]

def test_pop_region_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_a")
    removed = sample_admin_state.pop_address(address)

    assert "HOMELAND" in sample_admin_state.unit_hierarchy
    assert "region_a" not in sample_admin_state.unit_hierarchy["HOMELAND"]
    assert "district_a" in removed  # Confirm content was returned

    assert sample_admin_state.all_region_names() == ['region_b', 'region_c']


def test_add_region_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address = ("HOMELAND",)
    new_region = {"region_x": {"district_y": {}}}
    sample_admin_state.add_address(address + ("region_x",), new_region["region_x"])

    assert "region_x" in sample_admin_state.unit_hierarchy["HOMELAND"]
    assert sample_admin_state.unit_hierarchy["HOMELAND"]["region_x"]=={"district_y": {}}

def test_get_region_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address_1 = ("HOMELAND","region_a")
    address_2 = ("HOMELAND", "region_x")

    assert sample_admin_state.get_address(address_1)
    assert not sample_admin_state.get_address(address_2)

def test_find_region_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    
    assert sample_admin_state.find_address("region_a", "Region") == ('HOMELAND', 'region_a')
    assert sample_admin_state.find_address("region_x", "Region") is None

def test_find_and_pop_region_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    
    removed = sample_admin_state.find_and_pop("region_a", "Region")
    assert "HOMELAND" in sample_admin_state.unit_hierarchy
    assert "region_a" not in sample_admin_state.unit_hierarchy["HOMELAND"]
    assert "district_a" in removed  # Confirm content was returned

    with pytest.raises(ValueError, match=r"doesn't exist"):
        sample_admin_state.find_and_pop("region_x", "Region")

# --- TEST DISTRICT ADDRESS --- #

def test_pop_district_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_a", "district_a")
    removed = sample_admin_state.pop_address(address)

    assert "district_a" not in sample_admin_state.unit_hierarchy["HOMELAND"]["region_a"]
    assert removed == {}


def test_add_district_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_b")
    new_district_name = "district_z"
    new_district_data = {}

    sample_admin_state.add_address(address + (new_district_name,), new_district_data)

    assert "district_z" in sample_admin_state.unit_hierarchy["HOMELAND"]["region_b"]
    assert sample_admin_state.unit_hierarchy["HOMELAND"]["region_b"]["district_z"] == {}

def test_get_district_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address_1 = ("HOMELAND","region_a", "district_b") # Existent address
    address_2 = ("HOMELAND", "region_b", "district_z") # Nonexistent address

    assert sample_admin_state.get_address(address_1)
    assert not sample_admin_state.get_address(address_2)

def test_find_district_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    
    assert sample_admin_state.find_address("district_b", "District") == ("HOMELAND","region_a", "district_b")
    assert sample_admin_state.find_address("district_z", "District") is None

def test_find_and_pop_district_address(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    
    removed = sample_admin_state.find_and_pop("district_b", "District")
    assert removed == {}
    assert "district_b" not in sample_admin_state.unit_hierarchy["HOMELAND"]["region_a"]

    with pytest.raises(ValueError, match=r"doesn't exist"):
        sample_admin_state.find_and_pop("district_z", "District")

# --- ERROR HANDLING --- #

def test_pop_nonexistent_address_raises(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "region_x", "district_i")  # Invalid region
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_admin_state.pop_address(address)

def test_add_nonexistent_path_raises(change_test_setup):
    sample_admin_state = change_test_setup["administrative_state"]
    address = ("HOMELAND", "NonExistentRegion", "NewDistrict")
    with pytest.raises(ValueError, match=r"does not belong"):
        sample_admin_state.add_address(address, {})

# --- TESTS for the to_address_list method --- #

def test_pop_district_address(change_test_setup):
    valid_admin_state = change_test_setup["administrative_state"]
    valid_district_registry = change_test_setup["district_registry"]
    valid_region_registry = change_test_setup["region_registry"]

    try:
        valid_admin_state.verify_consistency(valid_region_registry, valid_district_registry)
    except ValueError:
        pytest.fail("verify_consistency() raised ValueError unexpectedly.")
    
    # Pop region only from the adm state, not from the region registry. Should return error.
    invalid_admin_state_1 = deepcopy(valid_admin_state)
    address_1 = ("HOMELAND", "region_a")
    _ = invalid_admin_state_1.pop_address(address_1)
    with pytest.raises(ValueError, match=r"Region .* doesn't belong to the current administrative state hierarchy"):
        invalid_admin_state_1.verify_consistency(valid_region_registry, valid_district_registry)

    # Add region only to the adm state, not to the region registry. Should return error.
    invalid_admin_state_2 = deepcopy(valid_admin_state)
    address_2 = ("HOMELAND", "region_x")
    invalid_admin_state_2.add_address(address_2, {"district_z": {}})
    with pytest.raises(ValueError, match=r"Region .* doesn't exist in the RegionRegistry"):
        invalid_admin_state_2.verify_consistency(valid_region_registry, valid_district_registry)

    # Pop district only from the adm state, not from the dist registry. Should return error.
    invalid_admin_state_3 = deepcopy(valid_admin_state)
    address_3 = ("HOMELAND", "region_a", "district_a")
    _ = invalid_admin_state_3.pop_address(address_3)
    with pytest.raises(ValueError, match=r"District .* doesn't belong to the current administrative state hierarchy"):
        invalid_admin_state_3.verify_consistency(valid_region_registry, valid_district_registry)

    # Add district only to the adm state, not to the dist registry. Should return error.
    invalid_admin_state_4 = deepcopy(valid_admin_state)
    address_4 = ("HOMELAND", "region_a", "district_x")
    invalid_admin_state_4.add_address(address_4, {})
    with pytest.raises(ValueError, match=r"District .* doesn't exist in the DistrictRegistry"):
        invalid_admin_state_4.verify_consistency(valid_region_registry, valid_district_registry)

    # Change region state timespan start and end to after 16-11-1938. Should return error.
    invalid_region_registry_1 = deepcopy(valid_region_registry)
    _, region_a_only_state, _ = invalid_region_registry_1.find_unit_state_by_date('region_a', datetime(1930,1,1))
    region_a_only_state.timespan = TimeSpan(start = datetime(1938,11,17), end = datetime(1938,11,18))
    with pytest.raises(ValueError, match=r"Region .* doesn't exist in the region registry"):
        valid_admin_state.verify_consistency(invalid_region_registry_1, valid_district_registry)

    # Change district state timespan start and end to after 16-11-1938. Should return error.
    invalid_district_registry_1 = deepcopy(valid_district_registry)
    _, district_a_only_state, _ = invalid_district_registry_1.find_unit_state_by_date('district_a', datetime(1930,1,1))
    district_a_only_state.timespan = TimeSpan(start = datetime(1938,11,17), end = datetime(1938,11,18))
    with pytest.raises(ValueError, match=r"District .* doesn't exist in the district registry"):
        valid_admin_state.verify_consistency(valid_region_registry, invalid_district_registry_1)

    # Create a new region state in 1930. The region state timespan doesn't encompass adm state timespan and so an error should be raised.
    invalid_region_registry_2 = deepcopy(valid_region_registry)
    _ = invalid_region_registry_2.create_next_unit_state('region_a', datetime(1931, 1, 1))
    with pytest.raises(ValueError, match=r"Region .* is not contained in its timespan .*"):
        valid_admin_state.verify_consistency(invalid_region_registry_2, valid_district_registry)

    # Create a new district state in 1930. The region state timespan doesn't encompass adm state timespan and so an error should be raised.
    invalid_district_registry_2 = deepcopy(valid_district_registry)
    _ = invalid_district_registry_2.create_next_unit_state('district_a', datetime(1931, 1, 1))
    with pytest.raises(ValueError, match=r"District .* is not contained in its timespan .*"):
        valid_admin_state.verify_consistency(valid_region_registry, invalid_district_registry_2)

def test_to_address_list(change_test_setup):
    valid_admin_state = change_test_setup["administrative_state"]
    district_registry = change_test_setup["district_registry"]
    region_registry = change_test_setup["region_registry"]

    default_list = valid_admin_state.to_address_list()
    correct_default_list = [
        ("ABROAD", "region_c", "district_e"),
        ("ABROAD", "region_c", "district_f"),
        ("HOMELAND", "region_a", "district_a"),
        ("HOMELAND", "region_a", "district_b"),
        ("HOMELAND", "region_b", "district_c"),
        ("HOMELAND", "region_b", "district_d"),
    ]
    assert default_list == correct_default_list

    only_homeland_list = valid_admin_state.to_address_list(only_homeland = True, region_registry = region_registry, district_registry = district_registry)
    correct_only_homeland_list = [
        ("region_a", "district_a"),
        ("region_a", "district_b"),
        ("region_b", "district_c"),
        ("region_b", "district_d"),
    ]
    assert only_homeland_list == correct_only_homeland_list

    with_variants_list = valid_admin_state.to_address_list(with_variants = True, region_registry = region_registry, district_registry = district_registry)
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
    district_a, district_a_state, _ = district_registry.find_unit_state_by_date('district_c', datetime(1930,1,1))
    district_a_state.current_name = 'DISTRICT_C'

    normal_names_id_list = valid_admin_state.to_address_list()
    correct_normal_names_id_list = [
        ("ABROAD", "region_c", "district_e"),
        ("ABROAD", "region_c", "district_f"),
        ("HOMELAND", "region_a", "district_a"),
        ("HOMELAND", "region_a", "district_b"),
        ("HOMELAND", "region_b", "district_c"),
        ("HOMELAND", "region_b", "district_d"),
    ]
    assert normal_names_id_list == correct_normal_names_id_list

    current_names_list = valid_admin_state.to_address_list(current_not_id = True, region_registry = region_registry, district_registry = district_registry)
    correct_current_names_list = [
        ("ABROAD", "region_c", "district_e"),
        ("ABROAD", "region_c", "district_f"),
        ("HOMELAND", "REGION_A", "district_a"),
        ("HOMELAND", "REGION_A", "district_b"),
        ("HOMELAND", "region_b", "DISTRICT_C"),
        ("HOMELAND", "region_b", "district_d"),
    ]
    assert current_names_list == correct_current_names_list


