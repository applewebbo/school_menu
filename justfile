local:
	python scripts/dev_server.py

requirements:
	uv pip compile --extra dev -o requirements-dev.txt pyproject.toml
	uv pip compile pyproject.toml -o requirements.txt
	uv pip install -r requirements-dev.txt -r requirements.txt

update_req:
	uv pip compile --upgrade --extra dev -o requirements-dev.txt pyproject.toml
	uv pip compile --upgrade pyproject.toml -o requirements.txt
	uv pip install -r requirements-dev.txt -r requirements.txt

checkmigrations:
	python manage.py makemigrations --check --no-input --dry-run

watch:
	bunx tailwindcss -i ./static/src/input.css -o ./static/css/tailwind.css --watch

test:
	pytest --reuse-db -s

quicktest:
	pytest -n 8 --reuse-db
