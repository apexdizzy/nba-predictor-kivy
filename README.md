# NBA Predictor — Kivy

Kivy conversion of the NBA Advanced Predictor. Use the "Load / Update from PDF" button to choose an NBA advanced stats PDF from your device. The app will extract team metrics, save them to Documents/teams_data.json, and allow you to run Monte Carlo predictions.

## Quick start (desktop/testing)

1. Create a virtualenv and install requirements:

```bash
pip install -r requirements.txt
```

2. Run the app:

```bash
python main.py
```

## Build Android APK (on Linux)

1. Install buildozer and Android SDK prerequisites.
2. Run:

```bash
buildozer init
# edit buildozer.spec if needed
buildozer -v android debug
```

The generated APK will be in `bin/`.
