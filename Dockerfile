FROM python:3.12-slim

WORKDIR /app

# System dependencies for PortAudio and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8181

CMD ["python", "-m", "uvicorn", "whisperflow.fast_server:app", \
     "--host", "0.0.0.0", "--port", "8181"]
