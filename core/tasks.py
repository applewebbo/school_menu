from django.core import management


def backup():
    return management.call_command("dbbackup")
