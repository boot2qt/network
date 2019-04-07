build:
	pyrcc5 -o network/resource.py -compress 9 -threshold 1 qml/resources.qrc
	python -m zipapp network -o ../build/network -c -p "/usr/bin/env python3"
	