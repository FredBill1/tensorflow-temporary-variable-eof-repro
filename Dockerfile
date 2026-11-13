FROM python:3.11-slim
ARG TF_VERSION=2.21.0
ARG TF_KERAS_VERSION=2.21.0
ENV TF_USE_LEGACY_KERAS=1 \
    CUDA_VISIBLE_DEVICES=-1 \
    PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir \
    "tensorflow==${TF_VERSION}" \
    "tf-keras==${TF_KERAS_VERSION}" \
    "numpy==1.26.4"
WORKDIR /app
COPY repro.py .
ENTRYPOINT ["python", "repro.py"]
