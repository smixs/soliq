import PyInstaller.__main__
import os

# Путь к иконке
icon_path = os.path.join('assets', 'icon.ico')

PyInstaller.__main__.run([
    'run_app.bat',
    '--onefile',
    '--icon=' + icon_path,
    '--name=Soliq Checkmate',
    '--noconsole',
    '--add-data=src;src',
    '--add-data=requirements.txt;.',
    '--hidden-import=streamlit',
    '--hidden-import=httpx',
    '--hidden-import=pandas',
    '--hidden-import=beautifulsoup4',
]) 