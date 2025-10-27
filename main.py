# main.py
import os
import json
import re
from functools import partial
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import mainthread
from kivy.core.window import Window
from plyer import filechooser
from pypdf import PdfReader
import numpy as np

# Optional: set a consistent window size for desktop testing
try:
    Window.size = (800, 600)
except Exception:
    pass

# -----------------------------
# File helpers
# -----------------------------
def get_documents_dir():
    \"\"\"Return a documents directory path. On Android attempt primary external storage, else use app_user_data.\"\"\"
    try:
        # Android-specific import (works on device)
        from android.storage import primary_external_storage_path
        base = primary_external_storage_path()
        docs = os.path.join(base, "Documents")
        os.makedirs(docs, exist_ok=True)
        return docs
    except Exception:
        # Fallback for desktop/testing
        base = App.get_running_app().user_data_dir if App.get_running_app() else os.path.expanduser("~")
        docs = os.path.join(base, "Documents")
        os.makedirs(docs, exist_ok=True)
        return docs

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -----------------------------
# Team data initialization
# -----------------------------
def initialize_teams_data():
    base_stats = {
        "GP": None, "W": None, "L": None, "MIN": None,
        "OffRtg": None, "DefRtg": None, "NetRtg": None,
        "AST%": None, "AST/TO": None, "AST Ratio": None,
        "OREB%": None, "DREB%": None, "REB%": None,
        "TOV%": None, "eFG%": None, "TS%": None,
        "PACE": None, "PIE": None, "POSS": None
    }

    team_names = [
        "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls",
        "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons",
        "Golden State Warriors", "Houston Rockets", "Indiana Pacers", "LA Clippers",
        "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks",
        "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
        "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
        "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs",
        "Toronto Raptors", "Utah Jazz", "Washington Wizards"
    ]

    return {t: base_stats.copy() for t in team_names}

# -----------------------------
# PDF extraction (kept algorithmic logic)
# -----------------------------
def extract_pdf_data(pdf_path, debug=False):
    \"\"\"Extracts team stats from the NBA Advanced Team Stats PDF.
    Returns a dict of structured stats per team.\"\"\"
    teams_data = {}
    try:
        reader = PdfReader(pdf_path)
        text = "\\n".join((page.extract_text() or "") for page in reader.pages)

        if debug:
            print("=== DEBUG: TEXT EXTRACTED (first 1000 chars) ===")
            print(text[:1000])
            print("================================================")

        # cleanup
        text = re.sub(r"NBA Advanced Team Stats.*?\\n#", "", text, flags=re.S)
        text = text.replace("\\n\\n", "\\n").strip()

        headers = [
            "GP", "W", "L", "MIN", "OffRtg", "DefRtg", "NetRtg", "AST%",
            "AST/TO", "AST Ratio", "OREB%", "DREB%", "REB%", "TOV%",
            "eFG%", "TS%", "PACE", "PIE", "POSS"
        ]

        pattern = re.compile(
            r"(\\d+)\\s+([A-Za-z .]+)\\s+"               # Rank + Team name
            r"(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+([\\d.]+)\\s+"    # GP W L MIN
            r"([\\d.]+)\\s+([\\d.-]+)\\s+"                # OffRtg DefRtg
            r"([\\d.-]+)\\s+([\\d.]+)\\s+([\\d.]+)\\s+"     # NetRtg AST% AST/TO
            r"([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)\\s+"      # AST Ratio OREB% DREB%
            r"([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)\\s+"      # REB% TOV% eFG%
            r"([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)"  # TS% PACE PIE POSS
        )

        matches = pattern.findall(text)
        if debug:
            print(f\"🔍 Found {len(matches)} team entries in text.\")

        for m in matches:
            try:
                team_name = m[1].strip()
                numeric_values = m[2:]
                stats = {}
                for key, val in zip(headers, numeric_values):
                    try:
                        stats[key] = float(val)
                    except Exception:
                        stats[key] = val
                teams_data[team_name] = stats
            except Exception as e:
                print(f\"⚠️ Skipped malformed entry: {e}\")

        if debug:
            print(f\"✅ Parsed {len(teams_data)} teams successfully.\")

        return teams_data

    except Exception as e:
        print(f\"❌ PDF extraction failed: {e}\")
        return {}

# -----------------------------
# Kivy Screens
# -----------------------------
from kivy.uix.modalview import ModalView
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button

class HomeScreen(Screen):
    pass

class TeamsScreen(Screen):
    team_list = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.refresh_team_list()

    def refresh_team_list(self):
        container = self.ids.team_list
        container.clear_widgets()
        app = App.get_running_app()
        data = app.teams_data or initialize_teams_data()
        for team in sorted(data.keys()):
            b = Button(text=team, size_hint_y=None, height=44)
            b.bind(on_release=partial(self.open_team_popup, team))
            container.add_widget(b)

    def load_pdf(self):
        # open Android file picker / desktop file chooser using Plyer
        try:
            filechooser.open_file(on_selection=self._file_chosen)
        except Exception:
            # fallback: try tkinter filedialog if running on desktop without plyer
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                path = filedialog.askopenfilename(filetypes=[(\"PDF Files\", \"*.pdf\")])
                if path:
                    self._file_chosen([path])
            except Exception as e:
                self.show_message('Error', f'File chooser not available: {e}')

    @mainthread
    def _file_chosen(self, selection):
        if not selection:
            return
        path = selection[0]
        app = App.get_running_app()
        extracted = extract_pdf_data(path)
        if extracted:
            app.teams_data = extracted
            docs = get_documents_dir()
            save_json(os.path.join(docs, 'teams_data.json'), extracted)
            self.refresh_team_list()
            self.show_message('Success', 'Team stats updated and saved to Documents.')
        else:
            self.show_message('Error', 'Failed to extract team stats from PDF.')

    def open_team_popup(self, team, *args):
        mv = ModalView(size_hint=(0.9, 0.9))
        box = BoxLayout(orientation='vertical')
        box.add_widget(Label(text=f'[b]{team} — Stats[/b]', markup=True, size_hint_y=None, height=40))
        data = App.get_running_app().teams_data.get(team, {})
        sv = ScrollView()
        gl = GridLayout(cols=1, size_hint_y=None)
        gl.bind(minimum_height=gl.setter('height'))
        for k, v in data.items():
            gl.add_widget(Label(text=f'{k}: {v}' if v is not None else f'{k}: —', size_hint_y=None, height=28))
        sv.add_widget(gl)
        box.add_widget(sv)
        box.add_widget(Button(text='Close', size_hint_y=None, height=44, on_release=lambda *a: mv.dismiss()))
        mv.add_widget(box)
        mv.open()

    def show_message(self, title, msg):
        mv = ModalView(size_hint=(0.8, 0.3))
        mv.add_widget(Label(text=f'[b]{title}[/b]\\n{msg}', markup=True))
        mv.open()

class PredictionScreen(Screen):
    t1 = StringProperty('Tap to select Team 1')
    t2 = StringProperty('Tap to select Team 2')

    def open_team_picker(self, target):
        app = App.get_running_app()
        teams = sorted(app.teams_data.keys())
        mv = ModalView(size_hint=(0.9, 0.9))
        sv = ScrollView()
        gl = GridLayout(cols=1, size_hint_y=None)
        gl.bind(minimum_height=gl.setter('height'))

        for team in teams:
            b = Button(text=team, size_hint_y=None, height=44)
            b.bind(on_release=lambda btn, t=team: self._select_team(target, t, mv))
            gl.add_widget(b)

        sv.add_widget(gl)
        mv.add_widget(sv)
        mv.open()

    def _select_team(self, target, team, modal):
        if target == 't1':
            self.t1 = team
        else:
            self.t2 = team
        modal.dismiss()

    def predict(self):
        if not self.t1 or not self.t2 or self.t1 == self.t2 or 'Tap to select' in (self.t1, self.t2):
            mv = ModalView(size_hint=(0.8, 0.3)); mv.add_widget(Label(text='Please select two different teams.')); mv.open(); return

        app = App.get_running_app()
        data = app.teams_data
        if self.t1 not in data or self.t2 not in data:
            mv = ModalView(size_hint=(0.8, 0.3)); mv.add_widget(Label(text='Team data missing.')); mv.open(); return

        def safe_floatify(stats):
            clean = {}
            for k, v in stats.items():
                try:
                    clean[k] = float(v)
                except Exception:
                    clean[k] = 0.0
            return clean

        s1, s2 = safe_floatify(data[self.t1]), safe_floatify(data[self.t2])

        try:
            def adjusted_offense(stats):
                return (
                    stats[\"OffRtg\"]
                    + 0.25 * stats[\"NetRtg\"]
                    + 0.5 * (stats[\"TS%\"] - 58)
                    + 0.5 * (stats[\"eFG%\"] - 55)
                    + 0.25 * (stats[\"AST%\"] - 60)
                    - 0.6 * (stats[\"TOV%\"] - 15)
                    + 0.25 * (stats[\"REB%\"] - 50)
                    + 0.25 * (stats[\"PIE\"] - 50)
                ) * 0.9

            adj1, adj2 = adjusted_offense(s1), adjusted_offense(s2)
            exp1_100 = (adj1 + s2[\"DefRtg\"]) / 2
            exp2_100 = (adj2 + s1[\"DefRtg\"]) / 2
            pace = (s1[\"PACE\"] + s2[\"PACE\"]) / 2
            score1 = exp1_100 * (pace / 100)
            score2 = exp2_100 * (pace / 100)

            np.random.seed(42)
            num_games = 5000
            std_dev = 8
            sim1 = np.random.normal(score1, std_dev, num_games)
            sim2 = np.random.normal(score2, std_dev, num_games)
            team1_wins = np.sum(sim1 > sim2)
            win_prob = team1_wins / num_games

            winner = self.t1 if win_prob >= 0.5 else self.t2
            loser = self.t2 if win_prob >= 0.5 else self.t1
            win_chance = max(win_prob, 1 - win_prob) * 100

            result_text = (
                f\"🏀 {winner} is projected to beat {loser}!\\n\\n\"
                f\"📊 Expected Score:\\n\"
                f\"{self.t1}: {score1:.1f}\\n\"
                f\"{self.t2}: {score2:.1f}\\n\\n\"
                f\"🔮 Win Probability: {win_chance:.1f}%\\n\"
                f\"📈 Expected Margin: {abs(score1 - score2):.1f} pts\\n\"
                f\"⚡ Total Points: {score1 + score2:.1f}\\n\"
                f\"📉 95% Score Range:\\n\"
                f\"   {self.t1}: {score1 - 16:.0f} – {score1 + 16:.0f}\\n\"
                f\"   {self.t2}: {score2 - 16:.0f} – {score2 + 16:.0f}\"
            )

            # save to Documents/prediction_history.json
            docs = get_documents_dir()
            hist_path = os.path.join(docs, 'prediction_history.json')
            history = load_json(hist_path) or []
            history.append({\"team1\": self.t1, \"team2\": self.t2, \"result\": result_text})
            save_json(hist_path, history)

            # pass result to Result screen
            App.get_running_app().root.get_screen('result').set_result(result_text)
            App.get_running_app().root.current = 'result'

        except Exception as e:
            mv = ModalView(size_hint=(0.9, 0.5)); mv.add_widget(Label(text='Prediction failed:\\n' + str(e))); mv.open()

class ResultScreen(Screen):
    def set_result(self, text):
        self.ids.result_label.text = text

class HistoryScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh_history()

    def refresh_history(self):
        container = self.ids.history_list
        container.clear_widgets()
        docs = get_documents_dir()
        hist_path = os.path.join(docs, 'prediction_history.json')
        history = load_json(hist_path) or []
        if not history:
            container.add_widget(Label(text='No predictions yet.'))
            return
        for entry in reversed(history):
            container.add_widget(Label(text=f\"{entry.get('team1')} vs {entry.get('team2')}\\n{entry.get('result')}\", halign='left', valign='top'))

# -----------------------------
# App & KV loader
# -----------------------------
KV = os.path.join(os.path.dirname(__file__), 'app.kv')

class NBAPredictorApp(App):
    teams_data = {}

    def build(self):
        # load stored teams data if present
        docs = get_documents_dir()
        teams_path = os.path.join(docs, 'teams_data.json')
        self.teams_data = load_json(teams_path) or initialize_teams_data()

        Builder.load_file(KV)
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(TeamsScreen(name='teams'))
        sm.add_widget(PredictionScreen(name='predict'))
        sm.add_widget(ResultScreen(name='result'))
        sm.add_widget(HistoryScreen(name='history'))
        return sm

if __name__ == '__main__':
    NBAPredictorApp().run()
