import pytest
from datetime import datetime
from data_models.adm_timespan import TimeSpan
from data_models.adm_state import AdministrativeState
from utils.exceptions import ConsistencyError

# --- TESTS for methods verifying mutual consistency of states --- #

def test_verify_adm_state_consistency(change_test_setup):
    valid_admin_state = change_test_setup["administrative_state"]
    valid_dist_registry = change_test_setup["dist_registry"]
    valid_region_registry = change_test_setup["region_registry"]

    with pytest.raises(ValueError, match=r"Wrong 'checkdate' argument"):
        valid_admin_state.verify_consistency(valid_region_registry, valid_dist_registry, check_date=datetime(1943,1,1))

    for check_date in [None, datetime(1923,1,1)]:
        try:
            valid_admin_state.verify_consistency(valid_region_registry, valid_dist_registry, check_date=check_date)
        except ValueError:
            pytest.fail("verify_consistency() raised ValueError unexpectedly.")
        
        # Pop region only from the adm state, not from the region registry. Should return error.
        invalid_admin_state_1 = valid_admin_state.model_copy(deep=True)
        address_1 = ("HOMELAND", "region_a")
        _ = invalid_admin_state_1.pop_address(address_1)
        with pytest.raises(ConsistencyError, match=r"Region .* doesn't belong to the current administrative state hierarchy"):
            invalid_admin_state_1.verify_consistency(valid_region_registry, valid_dist_registry, check_date=check_date)

        # Add region only to the adm state, not to the region registry. Should return error.
        invalid_admin_state_2 = valid_admin_state.model_copy(deep=True)
        address_2 = ("HOMELAND", "region_x")
        invalid_admin_state_2.add_address(address_2, {"district_z": {}})
        with pytest.raises(ConsistencyError, match=r"Region .* doesn't exist in the RegionRegistry"):
            invalid_admin_state_2.verify_consistency(valid_region_registry, valid_dist_registry, check_date=check_date)

        # Pop district only from the adm state, not from the dist registry. Should return error.
        invalid_admin_state_3 = valid_admin_state.model_copy(deep=True)
        address_3 = ("HOMELAND", "region_a", "district_a")
        _ = invalid_admin_state_3.pop_address(address_3)
        with pytest.raises(ConsistencyError, match=r"District .* doesn't belong to the current administrative state hierarchy"):
            invalid_admin_state_3.verify_consistency(valid_region_registry, valid_dist_registry, check_date=check_date)

        # Add district only to the adm state, not to the dist registry. Should return error.
        invalid_admin_state_4 = valid_admin_state.model_copy(deep=True)
        address_4 = ("HOMELAND", "region_a", "district_x")
        invalid_admin_state_4.add_address(address_4, {})
        with pytest.raises(ConsistencyError, match=r"District .* doesn't exist in the DistrictRegistry"):
            invalid_admin_state_4.verify_consistency(valid_region_registry, valid_dist_registry, check_date=check_date)

        # Change region state timespan start and end to after 16-11-1938. Should return error.
        invalid_region_registry_1 = valid_region_registry.model_copy(deep=True)
        _, region_a_only_state, _ = invalid_region_registry_1.find_unit_state_by_date('region_a', datetime(1930,1,1))
        region_a_only_state.timespan = TimeSpan(start = datetime(1938,11,17), end = datetime(1938,11,18))
        with pytest.raises(ConsistencyError, match=r"Region .* doesn't exist in the region registry"):
            valid_admin_state.verify_consistency(invalid_region_registry_1, valid_dist_registry, check_date=check_date)

        # Change district state timespan start and end to after 16-11-1938. Should return error.
        invalid_dist_registry_1 = valid_dist_registry.model_copy(deep=True)
        _, district_a_only_state, _ = invalid_dist_registry_1.find_unit_state_by_date('district_a', datetime(1930,1,1))
        district_a_only_state.timespan = TimeSpan(start = datetime(1938,11,17), end = datetime(1938,11,18))
        with pytest.raises(ConsistencyError, match=r"District .* doesn't exist in the district registry"):
            valid_admin_state.verify_consistency(valid_region_registry, invalid_dist_registry_1, check_date=check_date)

        # Create a new region state in 1930. The region state timespan doesn't encompass adm state timespan and so an error should be raised.
        invalid_region_registry_2 = valid_region_registry.model_copy(deep=True)
        _ = invalid_region_registry_2.create_next_unit_state('region_a', datetime(1931, 1, 1))
        with pytest.raises(ConsistencyError, match=r"Region .* is not contained in its timespan .*"):
            valid_admin_state.verify_consistency(invalid_region_registry_2, valid_dist_registry, check_date=check_date)

        # Create a new district state in 1930. The region state timespan doesn't encompass adm state timespan and so an error should be raised.
        invalid_dist_registry_2 = valid_dist_registry.model_copy(deep=True)
        _ = invalid_dist_registry_2.create_next_unit_state('district_a', datetime(1931, 1, 1))
        with pytest.raises(ConsistencyError, match=r"District .* is not contained in its timespan .*"):
            valid_admin_state.verify_consistency(valid_region_registry, invalid_dist_registry_2, check_date=check_date)

def test_verify_change_consistency(change_test_setup):
    valid_admin_state = change_test_setup["administrative_state"]
    valid_dist_registry = change_test_setup["dist_registry"]
    valid_region_registry = change_test_setup["region_registry"]