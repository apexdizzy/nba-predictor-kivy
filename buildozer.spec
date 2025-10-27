[app]
# (str) Title of your application
title = NBA Predictor

# (str) Package name
package.name = nba_predictor

# (str) Package domain (reverse domain notation)
package.domain = org.example

# (str) Source dir
source.dir = .

# (str) Application versioning (MUST be included)
version = 1.0.0

# (list) Application requirements
requirements = python3,kivy,numpy,pypdf,plyer

# (str) Entry point (main.py)
entrypoint = main.py

# (list) Permissions
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE


[buildozer]
log_level = 2
