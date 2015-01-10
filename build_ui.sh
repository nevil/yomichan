#!/bin/sh
pyuic5-2.7 ui/about.ui -o yomi_base/gen/about_ui.py
pyuic5-2.7 ui/preferences.ui -o yomi_base/gen/preferences_ui.py
pyuic5-2.7 ui/reader.ui -o yomi_base/gen/reader_ui.py
pyrcc5-2.7 ui/resources.qrc -o yomi_base/gen/resources_rc.py
