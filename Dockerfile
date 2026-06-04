FROM python:3.10-slim

# Dependências de sistema (EasyOCR precisa de libgl)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todos os arquivos do app
COPY . .

# Porta obrigatória no HF Spaces Docker = 7860
EXPOSE 7860

# Rodar o Streamlit na porta 7860
CMD ["streamlit", "run", "dashboard_streamlit.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.fileWatcherType=none", \
     "--browser.gatherUsageStats=false"]
