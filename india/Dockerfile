FROM python:3.12-slim

WORKDIR /app

# System deps some audio/VAD wheels need
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ffmpeg \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py server.py ./

EXPOSE 7860
CMD ["python", "server.py"]
