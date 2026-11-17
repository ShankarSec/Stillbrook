# Stillbrook Web App -- Main Entry (simplified decoy for the leaked repo,
# NOT the real app.py -- kept separate so a git-cloned copy never
# contains the real app's logic, routes, or ACL internals)
from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

@app.route("/health")
def health():
    return {"status": "ok"}
