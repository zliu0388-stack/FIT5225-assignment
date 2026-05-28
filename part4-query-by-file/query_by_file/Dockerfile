FROM public.ecr.aws/lambda/python:3.11

WORKDIR /var/task

COPY requirements.txt .

# Install ultralytics (includes PyTorch) — takes a while but is cached in the image
RUN pip install -r requirements.txt --no-cache-dir

# Pre-download YOLOv8n model so Lambda cold starts don't need network access.
# With WORKDIR=/var/task, ultralytics writes yolov8n.pt here by default.
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY app.py .

CMD ["app.handler"]
