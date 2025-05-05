import pytest
from datetime import datetime
import geopandas as gpd

from ..data_models.adm_timespan import TimeSpan
from ..data_models.adm_state import AdministrativeState
from ..data_models.adm_unit import *
from ..data_models.adm_change import *

############################################################################
#                           Definitions of fixtures                        #
############################################################################

# Use non-interactive matplotlib backend suitable for tests
import matplotlib
@pytest.fixture(autouse=True)
def set_matplotlib_backend():
    # Set the non-interactive Agg backend before any test
    matplotlib.use("Agg")

@pytest.fixture
def change_test_setup():
    # Common timespan
    timespan = TimeSpan(start=datetime(1921, 2, 19), end=datetime(1938, 11, 16))

    # Manually define the GeoJSON-like data as a Python dictionary
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"name": "district_a"}, "geometry": {"type": "Polygon", "coordinates": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]}},
            {"type": "Feature", "properties": {"name": "district_b"}, "geometry": {"type": "Polygon", "coordinates": [[(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]]}},
            {"type": "Feature", "properties": {"name": "district_c"}, "geometry": {"type": "Polygon", "coordinates": [[(0, 1), (1, 1), (1, 2), (0, 2), (0, 1)]]}},
            {"type": "Feature", "properties": {"name": "district_d"}, "geometry": {"type": "Polygon", "coordinates": [[(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)]]}},
            {"type": "Feature", "properties": {"name": "district_e"}, "geometry": {"type": "Polygon", "coordinates": [[(2, 0), (3, 0), (3, 1), (2, 1), (2, 0)]]}},
            {"type": "Feature", "properties": {"name": "district_f"}, "geometry": {"type": "Polygon", "coordinates": [[(2, 1), (3, 1), (3, 2), (2, 2), (2, 1)]]}}
        ]
    }

    # Convert the dictionary to a GeoDataFrame using GeoPandas
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])

    # Create districts
    district_registry = DistrictRegistry(unit_list=[])
    for suffix in ['a', 'b', 'c', 'd', 'e', 'f']:
        name_id = f"district_{suffix}"

        # Find the row in the GeoDataFrame for the current district (based on name_id)
        district_row = gdf[gdf['name'] == name_id]

        # Extract the geometry for the current district
        current_territory = district_row.geometry.iloc[0]

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
                    current_territory=current_territory
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
#                           ChangeMatter fixtures                          #
############################################################################

#UnitReform fixtures

@pytest.fixture
def parametrized_region_reform_matter():
    def _make(unit_type: str, current_name: str, to_reform_seat_name: str):
        return UnitReform(
            change_type="UnitReform",
            unit_type=unit_type,
            current_name=current_name,
            to_reform={
                "current_name": unit_type.lower()+"_a",
                "current_seat_name": to_reform_seat_name
            },
            after_reform={
                "current_name": f"{unit_type.lower()}_a_Reformed",
                "current_seat_name": "seat_a_Reformed"
            }
        )
    return _make

@pytest.fixture
def parametrized_region_change(parametrized_region_reform_matter):
    def _make(unit_type: str, current_name: str, to_reform_seat_name: str):
        matter = parametrized_region_reform_matter(unit_type, current_name, to_reform_seat_name)
        return Change(
            date=datetime(1922, 1, 1),
            source="Test Source",
            description="Test region reform",
            order=1,
            matter=matter,
            units_affected={"Region": [], "District": []}
        )
    return _make

@pytest.fixture
def region_reform_matter_fixture():
    # Setup a UnitReform instance for Region reform
    return UnitReform(
        change_type = "UnitReform",
        unit_type="Region",
        current_name="region_a",
        to_reform={"current_name": "region_a", "current_seat_name": "seat_region_a"},
        after_reform={"current_name": "region_a_Reformed", "current_seat_name": "seat_a_Reformed"}
    )

@pytest.fixture
def district_reform_matter_fixture():
    # Setup a UnitReform instance for District reform
    return UnitReform(
        change_type = "UnitReform",
        unit_type="District",
        current_name="district_a",
        to_reform={"current_dist_type": "w", "current_name": "district_a", "current_seat_name": "seat_a"},
        after_reform={"current_dist_type": "m", "current_name": "district_a_Reformed", "current_seat_name": "seat_a_Reformed"}
    )

# OneToMany fixtures

@pytest.fixture
def one_to_many_take_to_create_true_fixture(change_test_setup):
    return OneToManyTakeTo(
        create=True,
        current_name="district_x",
        district=change_test_setup["district_x"],
    )

@pytest.fixture
def one_to_many_take_to_create_false_fixture():
    return OneToManyTakeTo(
        create=False,
        current_name="district_b"
    )

@pytest.fixture
def one_to_many_matter_fixture(change_test_setup):
    return OneToMany(
        change_type="OneToMany",
        unit_attribute="territory",
        unit_type="District",
        take_from=OneToManyTakeFrom(current_name="district_a", delete_unit=True),
        take_to=[
            OneToManyTakeTo(create=False, current_name="district_b", weight_from=0.5),
            OneToManyTakeTo(create=True, current_name="district_x", district=change_test_setup["district_x"], weight_from=0.5),
        ]
    )

# ManyToOne fixtures

@pytest.fixture
def create_many_to_one_matter_fixture(change_test_setup):
    district_x = change_test_setup["district_x"]
    return ManyToOne(
        change_type="ManyToOne",
        unit_attribute="territory",
        unit_type="District",
        take_from=[
            ManyToOneTakeFrom(current_name="district_a", weight_from=0.6, delete_unit=True),
            ManyToOneTakeFrom(current_name="district_b", weight_from=0.4, delete_unit=False),
        ],
        take_to=ManyToOneTakeTo(
            create=True,
            current_name="district_x",
            district=district_x,
        ),
    )

@pytest.fixture
def reuse_many_to_one_matter_fixture():
    return ManyToOne(
        change_type="ManyToOne",
        unit_attribute="territory",
        unit_type="District",
        take_from=[
            ManyToOneTakeFrom(current_name="district_c", weight_from=0.5, delete_unit=False),
            ManyToOneTakeFrom(current_name="district_d", weight_from=0.5, delete_unit=True),
        ],
        take_to=ManyToOneTakeTo(
            create=False,
            current_name="district_e",
        ),
    )

# ChangeAdmState fixtures

@pytest.fixture
def region_change_adm_state_matter_fixture():
    return ChangeAdmState(
        change_type="ChangeAdmState",
        take_from=("ABROAD", "region_c"),
        take_to=("HOMELAND", "region_c"),
    )

@pytest.fixture
def district_change_adm_state_matter_fixture():
    return ChangeAdmState(
        change_type="ChangeAdmState",
        take_from=("HOMELAND", "region_a", "district_a"),
        take_to=("HOMELAND", "region_b", "district_a"),
    )