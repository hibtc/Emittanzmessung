Emittanzmessung
===============

Auswertescripts für die Emittanzmessung anhand der FWHM Breiten aus der
Dreigitter-Prozedur.


Benutzung
~~~~~~~~~

- Zunächst die Dreigitter-Prozedur fahren und den Ausgabeordner kopieren.

- Zeitnah (oder gleichzeitig) ``download_settings.py`` ausführen um die
  Magnetstärken auszulesen und lokal zu speichern.

- Das dem verwendeten VAcc entsprechende MAD-X Modell ausfindig machen.

- Anschließend ``calc_emit.py`` ausführen mit den drei Parametern:
  ``<DATA_FOLDER> <MADX_MODEL_FILE> <MADX_SEQUENCE_NAME>``, zum Beispiel::

    python calc_emit.py Emittanzmessung_p_4300 ../hit_models/hht3/run.madx hht3

- Zuletzt ``plot_emit.py`` ausführen
