@echo off
title 📊 Dashboard Correoto
cd /d "C:\Users\Crypto Bull\Desktop\Agente Local"
echo 🚀 A iniciar o Dashboard...
python -c "from dashboard.server import start_dashboard; start_dashboard(host='0.0.0.0', port=3000)"
pause
