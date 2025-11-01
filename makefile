.PHONY: test lint package clean docs

test:
	pytest-3 -v

lint:
	python3 -m flake8 dotsync --count --statistics --show-source

package:
	python3 setup.py sdist bdist_wheel

clean:
	rm -rf build dist dotsync.egg-info

docs:
	sphinx-build -M html docs docs/_build
