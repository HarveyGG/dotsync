.PHONY: test lint package clean docs

test:
	pytest-3 -v

lint:
	ruff check dotsync

package:
	python3 setup.py sdist bdist_wheel

clean:
	rm -rf build dist dotsync.egg-info

docs:
	sphinx-build -M html docs docs/_build
