type_check:
	python3 -m pip install mypy
	mypy roam_sanity/ scripts/ app/main.py

lint:
	python3 -m pip install pylint
	pylint roam_sanity/ scripts/ app/main.py
