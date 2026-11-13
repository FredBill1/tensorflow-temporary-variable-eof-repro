# syntax=docker/dockerfile:1.7
# TensorFlow 2.18.1 CPU-only, compiled with targeted TFRES C++ logging.
# Required: Docker BuildKit and Linux amd64 (WSL2 Docker Desktop works).
FROM --platform=linux/amd64 python:3.11-trixie AS builder
ARG BAZEL_JOBS=4
ARG BAZEL_RAM_MB=12288
ENV DEBIAN_FRONTEND=noninteractive \
    TF_NEED_CUDA=0 TF_NEED_ROCM=0 TF_NEED_TENSORRT=0 \
    TF_DOWNLOAD_CLANG=0 TF_SET_ANDROID_WORKSPACE=0 \
    TF_NEED_CLANG=1 TF_PYTHON_VERSION=3.11 \
    PYTHON_BIN_PATH=/usr/local/bin/python3 \
    PYTHON_LIB_PATH=/usr/local/lib/python3.11/site-packages \
    USE_DEFAULT_PYTHON_LIB_PATH=1 \
    CC=/usr/bin/clang-17 \
    BAZEL_COMPILER=/usr/bin/clang-17 \
    CLANG_COMPILER_PATH=/usr/bin/clang-17 \
    CC_OPT_FLAGS="-Wno-sign-compare -O3" \
    TF_CPP_MIN_LOG_LEVEL=0
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git curl ca-certificates unzip zip clang-17 lld-17 \
      libssl-dev pkg-config patchelf cmake ninja-build \
      default-jdk-headless && \
    rm -rf /var/lib/apt/lists/*
# Bazelisk reads .bazelversion in TensorFlow checkout (6.5.0).
RUN curl -fL --retry 5 \
      https://github.com/bazelbuild/bazelisk/releases/download/v1.25.0/bazelisk-linux-amd64 \
      -o /usr/local/bin/bazel && chmod +x /usr/local/bin/bazel
RUN python -m pip install --no-cache-dir 'numpy==1.26.4' 'packaging' 'wheel' 'setuptools'
RUN git clone --depth 1 --branch v2.18.1 \
      https://github.com/tensorflow/tensorflow.git /opt/tensorflow && \
    git -C /opt/tensorflow rev-parse HEAD > /opt/source_revision.txt
COPY diagnostics/patch_tf.py /opt/patch_tf.py
RUN python /opt/patch_tf.py /opt/tensorflow
WORKDIR /opt/tensorflow
RUN python configure.py </dev/null && \
    test -s .tf_configure.bazelrc
# Use a cache mount to preserve the expensive Bazel outputs across builds.
RUN --mount=type=cache,target=/root/.cache/bazel,sharing=locked \
    bazel build \
      --jobs="${BAZEL_JOBS}" \
      --local_ram_resources="${BAZEL_RAM_MB}" \
      --config=opt \
      --repo_env=TF_PYTHON_VERSION=3.11 \
      --repo_env=USE_PYWRAP_RULES=1 \
      --repo_env=WHEEL_NAME=tensorflow_cpu \
      //tensorflow/tools/pip_package:wheel && \
    mkdir -p /opt/wheels && \
    cp bazel-bin/tensorflow/tools/pip_package/wheel_house/*.whl /opt/wheels/ && \
    ls -lh /opt/wheels

# Match the original reproduction's exact Python base digest when possible.
FROM --platform=linux/amd64 python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535
ENV TF_USE_LEGACY_KERAS=1 CUDA_VISIBLE_DEVICES=-1 \
    TF_CPP_MIN_LOG_LEVEL=0 PYTHONUNBUFFERED=1
COPY --from=builder /opt/wheels /tmp/wheels
COPY --from=builder /opt/source_revision.txt /app/source_revision.txt
COPY --from=builder /opt/tensorflow/tfres_patch_manifest.json /app/tfres_patch_manifest.json
RUN python -m pip install --no-cache-dir 'numpy==1.26.4' /tmp/wheels/*.whl && \
    python -m pip install --no-cache-dir --no-deps 'tf-keras==2.18.0' && \
    python -c "import tensorflow as tf; import tf_keras; print('TFRES_WHEEL', tf.__version__, tf_keras.__version__)" && \
    rm -rf /tmp/wheels
WORKDIR /app
COPY repro.py /app/repro.py
ENTRYPOINT ["python", "/app/repro.py"]
