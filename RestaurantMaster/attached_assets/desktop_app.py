
import streamlit_native as sn
from streamlit.web import bootstrap
import os

def run_streamlit():
    os.environ["STREAMLIT_SERVER_PORT"] = "8501"
    bootstrap.run("app.py", "", [], {})

if __name__ == "__main__":
    config = sn.Config()
    config.app_name = "Restoran Stok Takip"
    config.icon_path = "generated-icon.png"
    config.window_size = (1200, 800)
    config.min_window_size = (800, 600)
    
    app = sn.StreamlitNative(config)
    app.run(run_streamlit)
