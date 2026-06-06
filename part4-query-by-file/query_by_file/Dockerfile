FROM python:3.9
WORKDIR /function
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY func.py .
ENTRYPOINT ["fdk", "/function/func.py", "handler"]
