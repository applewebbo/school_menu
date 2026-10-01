from unittest.mock import patch

from notifications.apps import NotificationsConfig


def test_ready_patches_on_macos_dev(settings):
    settings.ENVIRONMENT = "dev"
    with patch("sys.platform", "darwin"):
        with patch.object(NotificationsConfig, "_patch_qcluster_mp_context") as mocked:
            NotificationsConfig("notifications", __import__("notifications")).ready()

    mocked.assert_called_once()


def test_ready_skips_patch_outside_dev(settings):
    settings.ENVIRONMENT = "prod"
    with patch("sys.platform", "darwin"):
        with patch.object(NotificationsConfig, "_patch_qcluster_mp_context") as mocked:
            NotificationsConfig("notifications", __import__("notifications")).ready()

    mocked.assert_not_called()


def test_ready_skips_patch_outside_macos(settings):
    settings.ENVIRONMENT = "dev"
    with patch("sys.platform", "linux"):
        with patch.object(NotificationsConfig, "_patch_qcluster_mp_context") as mocked:
            NotificationsConfig("notifications", __import__("notifications")).ready()

    mocked.assert_not_called()


def test_patch_qcluster_mp_context_hides_fork(monkeypatch):
    monkeypatch.setattr(
        "multiprocessing.get_all_start_methods", lambda: ["fork", "spawn"]
    )

    NotificationsConfig._patch_qcluster_mp_context()

    import multiprocessing

    assert "fork" not in multiprocessing.get_all_start_methods()
    assert "spawn" in multiprocessing.get_all_start_methods()
