import pytest
from datetime import datetime
from utils import *

############################################################################
#                       load_and_standardize_csv tests                     #
############################################################################

# Test for UnitState class initialization and basic functionality
def load_and_standardize_csv(change_test_setup):
    dist_registry = change_test_setup["dist_registry"]
    region_registry = change_test_setup["region_registry"]

    # Valid csv with name ids
    df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_1.csv", dist_registry, region_registry)
    assert list(df["Region"]) == ["region_a", "region_b"]
    assert list(df["District"]) == ["district_a", "district_c"]

    # CSV with additional columns - should be kept untouched
    df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_2.csv", dist_registry, region_registry)
    assert list(df["Region"]) == ["region_a", "region_b"]
    assert list(df["District"]) == ["district_a", "district_c"]
    assert list(df["Additional_Column_1"]) == ["additional_value_1", "additional_value_2"]
    assert list(df["Additional_Column_2"]) == ["additional_value_3", "additional_value_4"]

    # CSV with no "Region" column
    with pytest.raises(ValueError, match=r"must contain 'Region' and 'District' column"):
        df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_3.csv", dist_registry, region_registry)

    # CSV with no "District" column
    with pytest.raises(ValueError, match=r"must contain 'Region' and 'District' column"):
        df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_4.csv", dist_registry, region_registry)
    
    # With alternative region names
    df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_5.csv", dist_registry, region_registry)
    assert list(df["Region"]) == ["region_a", "region_b"]
    assert list(df["District"]) == ["district_a", "district_c"]

    # With alternative district names
    df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_6.csv", dist_registry, region_registry)
    assert list(df["Region"]) == ["region_a", "region_b"]
    assert list(df["District"]) == ["district_a", "district_c"]

    # With a wrong region name
    with pytest.raises(ValueError, match=r"Region names ['region_x'] do not exist"):
        df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_7.csv", dist_registry, region_registry)

    # With a wrong region name
    with pytest.raises(ValueError, match=r"District names ['district_x'] do not exist"):
        df = load_and_standardize_csv("tests/test_input/load_and_standardize_csv/test_8.csv", dist_registry, region_registry)

