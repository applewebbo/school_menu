local:
	python manage.py tailwind --settings=core.settings.dev runserver

requirements:
	uv pip compile --extra dev -o requirements-dev.txt pyproject.toml
	uv pip compile pyproject.toml -o requirements.txt
	uv pip install -r requirements-dev.txt -r requirements.txt

checkmigrations:
	python manage.py makemigrations --check --no-input --dry-run

watch:
	python manage.py tailwind watch

test:
	pytest -n 8 --reuse-db
