ALL: translations documentation

translations: po/de/LC_MESSAGES/context-annotator.mo

po/de/LC_MESSAGES/context-annotator.mo: po/context-annotator.pot po/de.po
	mkdir -p po/de/LC_MESSAGES
	msgfmt -c -v -o po/de/LC_MESSAGES/context-annotator.mo po/de.po

documentation:
	cd doc && make html