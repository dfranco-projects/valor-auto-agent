import subprocess
import sys
from pathlib import Path


def main() -> None:
    app = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], check=False)
