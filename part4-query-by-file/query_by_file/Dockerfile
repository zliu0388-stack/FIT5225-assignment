FROM python:3.9-slim
WORKDIR /function

# System deps required by Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libjpeg62-turbo libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU-only — must use the PyTorch wheel index, not PyPI
RUN pip install --no-cache-dir \
    torch==2.1.2+cpu torchvision==0.16.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Model weights and function code
COPY model.pt .
COPY func.py .

ENTRYPOINT ["fdk", "/function/func.py", "handler"]
