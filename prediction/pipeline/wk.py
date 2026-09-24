"""START = first week still to be played (= Sleeper league last_scored_leg + 1), from week.json in the run dir."""
import json
START = json.load(open("week.json"))["start"]
