import subprocess
import threading


def run_server():
    subprocess.run(
        "python manage.py runserver --settings=core.settings.dev",
        shell=True,
    )


def run_tailwind():
    subprocess.run(
        "bunx tailwindcss -i ./static/src/input.css -o ./static/css/tailwind.css --watch",
        shell=True,
    )


threading.Thread(target=run_server).start()
threading.Thread(target=run_tailwind).start()
