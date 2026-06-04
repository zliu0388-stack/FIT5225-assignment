FROM public.ecr.aws/lambda/python:3.12

# Base image already has curl-minimal; install tar+xz for static ffmpeg
# and glib2/mesa-libGL so opencv (pulled in by megadetector) can import cv2.
RUN dnf install -y tar xz glib2 mesa-libGL && dnf clean all \
    && curl -fsSL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz \
    && mkdir -p /opt/ffmpeg /opt/bin \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /opt/ffmpeg --strip-components=1 \
    && ln -sf /opt/ffmpeg/ffmpeg /opt/bin/ffmpeg \
    && ln -sf /opt/ffmpeg/ffprobe /opt/bin/ffprobe \
    && chmod +x /opt/bin/ffmpeg /opt/bin/ffprobe \
    && rm -f /tmp/ffmpeg.tar.xz

COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# The provided species model.pt is an onnx2torch-converted model, so torch.load
# needs onnx2torch's classes. Install it in a separate layer: its protobuf>=4.25
# requirement conflicts with ultralytics-yolov5's protobuf<=3.20.1 pin at resolve
# time, but a standalone upgrade only warns and works fine at runtime.
RUN pip install --no-cache-dir onnx2torch==1.5.15

# yolov5 (used by megadetector) still imports pkg_resources, which setuptools>=81
# removed. torch pulls in setuptools 82, so pin it back below 81 as the last step.
RUN pip install --no-cache-dir "setuptools<81"

COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["handlers.auto_tag_from_s3.handler"]
