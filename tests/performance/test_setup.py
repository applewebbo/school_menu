"""
Dummy test to verify performance testing infrastructure setup
This test ensures fixtures work correctly and provides coverage
"""

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.performance]


def test_performance_test_config_fixture(performance_test_config):
    """Verify performance_test_config fixture is accessible and configured correctly"""
    assert performance_test_config is not None
    assert performance_test_config["school_count"] == 100
    assert performance_test_config["user_count"] == 50
    assert "acceptable_query_count" in performance_test_config
    assert "acceptable_response_time_ms" in performance_test_config


def test_large_dataset_fixture(large_dataset):
    """Verify large_dataset fixture creates test data correctly"""
    assert large_dataset is not None
    assert "schools" in large_dataset
    assert "users" in large_dataset
    assert large_dataset["school_count"] == 100
    assert len(large_dataset["schools"]) == 100
    # One user per school due to OneToOneField
    assert len(large_dataset["users"]) == 100
