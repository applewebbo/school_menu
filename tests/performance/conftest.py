import pytest

from tests.school_menu.factories import SchoolFactory, SimpleMealFactory

# Automatically mark all tests in this directory as performance tests
pytestmark = pytest.mark.performance


@pytest.fixture(scope="session")
def performance_test_config():
    """Configuration for performance tests"""
    return {
        "school_count": 100,  # Realistic dataset size
        "meal_count_per_school": 200,  # 4 weeks × 5 days × 10 meal types
        "user_count": 50,
        "acceptable_query_count": {
            "school_list": 2,  # With select_related
            "school_detail": 3,
            "api_schools": 2,
        },
        "acceptable_response_time_ms": {
            "school_list": 200,  # 200ms
            "school_detail": 150,
            "api_schools": 100,
        },
    }


@pytest.fixture
def large_dataset(db, performance_test_config):
    """Create large realistic dataset for performance testing"""
    # Create schools (each school creates its own user due to OneToOneField)
    schools = []
    for i in range(performance_test_config["school_count"]):
        school = SchoolFactory(is_published=True)
        schools.append(school)

        # Create meals for each school (4 weeks × 5 days × 3 types = 60 meals)
        for week in range(1, 5):
            for day in range(1, 6):
                for meal_type in ["S", "G", "L"]:
                    SimpleMealFactory(
                        school=school, week=week, day=day, season=1, type=meal_type
                    )

    # Collect all users created by SchoolFactory
    users = [school.user for school in schools]

    return {
        "schools": schools,
        "users": users,
        "school_count": len(schools),
    }
