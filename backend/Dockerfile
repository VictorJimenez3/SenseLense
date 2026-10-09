FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN useradd -m -u 1000 user && chown -R user /app
USER user
ENV HOME=/home/user

# Pre-download DeepFace emotion weights so cold start is fast.
RUN python -c "from deepface import DeepFace; import numpy as np; DeepFace.analyze(np.zeros((48,48,3),dtype='uint8'), actions=['emotion'], enforce_detection=False, silent=True, detector_backend='opencv')"

ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "python seed.py && exec gunicorn -w 1 --threads 4 --timeout 120 -b 0.0.0.0:${PORT} app:app"]
