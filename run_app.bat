@echo off
echo Starting Soliq Checkmate...
start /min streamlit run src/app.py
timeout /t 2 /nobreak
start http://localhost:8501
exit 