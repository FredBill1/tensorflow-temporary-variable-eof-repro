# TensorFlow `TemporaryVariable` survives dataset EOF

https://github.com/tensorflow/tensorflow/issues/130303

Minimal CPU reproduction of `AlreadyExistsError` in **TensorFlow 2.18.1 and 2.21.0**, with **legacy TF-Keras**. No GPU, distribution strategy, or custom C++ build required.

## Reproduce (Linux x86-64 / Docker)

```bash
docker build --platform linux/amd64 -t tf-tempvar:221 .
docker run --rm --cpus=8 tf-tempvar:221                       # FAILS (AddN + unknown cardinality)
docker run --rm --cpus=8 tf-tempvar:221 --known-cardinality   # PASSES
docker run --rm --cpus=8 tf-tempvar:221 --stack               # PASSES
```

<details>

<summary>Observed output</summary>

```log
$ docker run --rm --cpus=8 tf-tempvar:221                       # FAILS (AddN + unknown cardinality)
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1794579043.792556       1 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
I0000 00:00:1794579043.792839       1 cudart_stub.cc:31] Could not find cuda drivers on your machine, GPU will not be used.
I0000 00:00:1794579044.877451       1 cpu_feature_guard.cc:227] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 AVX_VNNI AVX_VNNI_INT8 AVX_NE_CONVERT FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1794579047.288676       1 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
I0000 00:00:1794579047.289036       1 cudart_stub.cc:31] Could not find cuda drivers on your machine, GPU will not be used.
TensorFlow: 2.21.0 Keras: tf_keras.src.engine.training
E0000 00:00:1794579047.605945       1 cuda_platform.cc:52] failed call to cuInit: INTERNAL: CUDA error: Failed call to cuInit: UNKNOWN ERROR (303)
Cardinality: -2 sum: AddN
I0000 00:00:1794579047.704598       1 generator_dataset_op.cc:213] Memory patch applied: M_TRIM_THRESHOLD=128 kb was set.
Epoch 1/3
4/4 - 1s - loss: 0.4239 - binary_accuracy: 0.5000 - val_loss: 1.0595 - val_binary_accuracy: 0.0000e+00 - 1s/epoch - 263ms/step
Epoch 2/3
W0000 00:00:1794579048.766386      52 op_kernel.cc:1858] OP_REQUIRES failed at variable_ops.cc:119 : ALREADY_EXISTS: Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
W0000 00:00:1794579048.769876      52 local_rendezvous.cc:412] Local rendezvous is aborting with status: ALREADY_EXISTS: Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
         [[{{node DirectSumLoss/AddN/tmp_var}}]]
Traceback (most recent call last):
  File "/app/repro.py", line 92, in <module>
    main()
  File "/app/repro.py", line 88, in main
    model.fit(train, validation_data=validation, epochs=3, verbose=2)
  File "/usr/local/lib/python3.11/site-packages/tf_keras/src/utils/traceback_utils.py", line 70, in error_handler
    raise e.with_traceback(filtered_tb) from None
  File "/usr/local/lib/python3.11/site-packages/tensorflow/python/eager/execute.py", line 53, in quick_execute
    tensors = pywrap_tfe.TFE_Py_Execute(ctx._handle, device_name, op_name,
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tensorflow.python.framework.errors_impl.AlreadyExistsError: Graph execution error:

Detected at node DirectSumLoss/AddN/tmp_var defined at (most recent call last):
<stack traces unavailable>
Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
         [[{{node DirectSumLoss/AddN/tmp_var}}]] [Op:__inference_train_function_1069]
```

```log
$ docker run --rm --cpus=8 tf-tempvar:221 --known-cardinality   # PASSES
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1794579117.403483       1 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
I0000 00:00:1794579117.403711       1 cudart_stub.cc:31] Could not find cuda drivers on your machine, GPU will not be used.
I0000 00:00:1794579117.433988       1 cpu_feature_guard.cc:227] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 AVX_VNNI AVX_VNNI_INT8 AVX_NE_CONVERT FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1794579118.495473       1 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
I0000 00:00:1794579118.495743       1 cudart_stub.cc:31] Could not find cuda drivers on your machine, GPU will not be used.
TensorFlow: 2.21.0 Keras: tf_keras.src.engine.training
E0000 00:00:1794579118.620571       1 cuda_platform.cc:52] failed call to cuInit: INTERNAL: CUDA error: Failed call to cuInit: UNKNOWN ERROR (303)
Cardinality: 4 sum: AddN
I0000 00:00:1794579118.738450       1 generator_dataset_op.cc:213] Memory patch applied: M_TRIM_THRESHOLD=128 kb was set.
Epoch 1/3
4/4 - 0s - loss: 0.4239 - binary_accuracy: 0.5000 - val_loss: 1.0595 - val_binary_accuracy: 0.0000e+00 - 484ms/epoch - 121ms/step
Epoch 2/3
4/4 - 0s - loss: 0.4224 - binary_accuracy: 0.5039 - val_loss: 1.0511 - val_binary_accuracy: 0.0000e+00 - 52ms/epoch - 13ms/step
Epoch 3/3
4/4 - 0s - loss: 0.4208 - binary_accuracy: 0.5000 - val_loss: 1.0428 - val_binary_accuracy: 0.0000e+00 - 49ms/epoch - 12ms/step
```

```log
$ docker run --rm --cpus=8 tf-tempvar:221 --stack               # PASSES
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1794579149.699777       1 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
I0000 00:00:1794579149.699984       1 cudart_stub.cc:31] Could not find cuda drivers on your machine, GPU will not be used.
I0000 00:00:1794579149.731487       1 cpu_feature_guard.cc:227] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 AVX_VNNI AVX_VNNI_INT8 AVX_NE_CONVERT FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1794579150.709487       1 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
I0000 00:00:1794579150.709749       1 cudart_stub.cc:31] Could not find cuda drivers on your machine, GPU will not be used.
TensorFlow: 2.21.0 Keras: tf_keras.src.engine.training
E0000 00:00:1794579150.816563       1 cuda_platform.cc:52] failed call to cuInit: INTERNAL: CUDA error: Failed call to cuInit: UNKNOWN ERROR (303)
Cardinality: -2 sum: Pack+Sum
I0000 00:00:1794579150.912238       1 generator_dataset_op.cc:213] Memory patch applied: M_TRIM_THRESHOLD=128 kb was set.
Epoch 1/3
4/4 - 1s - loss: 0.4239 - binary_accuracy: 0.5000 - val_loss: 1.0595 - val_binary_accuracy: 0.0000e+00 - 1s/epoch - 264ms/step
Epoch 2/3
4/4 - 0s - loss: 0.4224 - binary_accuracy: 0.5039 - val_loss: 1.0514 - val_binary_accuracy: 0.0000e+00 - 47ms/epoch - 12ms/step
Epoch 3/3
4/4 - 0s - loss: 0.4209 - binary_accuracy: 0.5000 - val_loss: 1.0430 - val_binary_accuracy: 0.0000e+00 - 58ms/epoch - 15ms/step
```

</details>


The failing run completes epoch 1, then fails at the beginning of epoch 2:

```text
AlreadyExistsError: Graph execution error
Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/...
[[{{node DirectSumLoss/AddN/tmp_var}}]]
```

Also reproduced with TensorFlow **2.18.1** and **nightly 2.23.0-dev20261111**:

```bash
docker build --platform linux/amd64 \
  --build-arg TF_VERSION=2.18.1 --build-arg TF_KERAS_VERSION=2.18.0 \
  -t tf-tempvar:218 .
docker run --rm --cpus=8 tf-tempvar:218  # FAILS
```

```bash
docker build --platform linux/amd64 \
  -f Dockerfile.nightly \
  -t tf-tempvar:nightly .
docker run --rm --cpus=8 tf-tempvar:nightly  # FAILS
```

<details>

<summary>Observed output</summary>

```log
$ docker run --rm --cpus=8 tf-tempvar:218  # FAILS
2026-11-13 14:17:19.541559: I tensorflow/core/util/port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
2026-11-13 14:17:19.541963: I external/local_xla/xla/tsl/cuda/cudart_stub.cc:32] Could not find cuda drivers on your machine, GPU will not be used.
2026-11-13 14:17:19.544226: I external/local_xla/xla/tsl/cuda/cudart_stub.cc:32] Could not find cuda drivers on your machine, GPU will not be used.
2026-11-13 14:17:19.549504: E external/local_xla/xla/stream_executor/cuda/cuda_fft.cc:477] Unable to register cuFFT factory: Attempting to register factory for plugin cuFFT when one has already been registered
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
E0000 00:00:1794579439.561158       1 cuda_dnn.cc:8310] Unable to register cuDNN factory: Attempting to register factory for plugin cuDNN when one has already been registered
E0000 00:00:1794579439.564725       1 cuda_blas.cc:1418] Unable to register cuBLAS factory: Attempting to register factory for plugin cuBLAS when one has already been registered
2026-11-13 14:17:19.578714: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 AVX_VNNI AVX_VNNI_INT8 AVX_NE_CONVERT FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
TensorFlow: 2.18.1 Keras: tf_keras.src.engine.training
2026-11-13 14:17:20.739331: E external/local_xla/xla/stream_executor/cuda/cuda_driver.cc:152] failed call to cuInit: INTERNAL: CUDA error: Failed call to cuInit: UNKNOWN ERROR (303)
Cardinality: -2 sum: AddN
Epoch 1/3
2026-11-13 14:17:21.741284: I tensorflow/core/framework/local_rendezvous.cc:405] Local rendezvous is aborting with status: OUT_OF_RANGE: End of sequence
         [[{{node IteratorGetNext}}]]
4/4 - 1s - loss: 0.4239 - binary_accuracy: 0.5000 - val_loss: 1.0595 - val_binary_accuracy: 0.0000e+00 - 995ms/epoch - 249ms/step
Epoch 2/3
2026-11-13 14:17:21.841803: W tensorflow/core/framework/op_kernel.cc:1841] OP_REQUIRES failed at variable_ops.cc:119 : ALREADY_EXISTS: Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
2026-11-13 14:17:21.841908: I tensorflow/core/framework/local_rendezvous.cc:405] Local rendezvous is aborting with status: ALREADY_EXISTS: Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
         [[{{node DirectSumLoss/AddN/tmp_var}}]]
Traceback (most recent call last):
  File "/app/repro.py", line 82, in <module>
    main()
  File "/app/repro.py", line 78, in main
    model.fit(train, validation_data=validation, epochs=3, verbose=2)
  File "/usr/local/lib/python3.11/site-packages/tf_keras/src/utils/traceback_utils.py", line 70, in error_handler
    raise e.with_traceback(filtered_tb) from None
  File "/usr/local/lib/python3.11/site-packages/tensorflow/python/eager/execute.py", line 53, in quick_execute
    tensors = pywrap_tfe.TFE_Py_Execute(ctx._handle, device_name, op_name,
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tensorflow.python.framework.errors_impl.AlreadyExistsError: Graph execution error:

Detected at node DirectSumLoss/AddN/tmp_var defined at (most recent call last):
<stack traces unavailable>
Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
         [[{{node DirectSumLoss/AddN/tmp_var}}]] [Op:__inference_train_function_1069]
```

```log
$ docker run --rm --cpus=8 tf-tempvar:nightly  # FAILS
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1794582317.224757       1 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
I0000 00:00:1794582317.271974       1 cpu_feature_guard.cc:227] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 AVX_VNNI AVX_VNNI_INT8 AVX_NE_CONVERT FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
TensorFlow: 2.23.0-dev20261111 Keras: tf_keras.src.engine.training
E0000 00:00:1794582318.476525       1 cuda_platform.cc:57] failed call to cuInit: INTERNAL: CUDA error: Failed call to cuInit: UNKNOWN ERROR (303)
=== Source Location Trace: ===
external/xla/xla/stream_executor/cuda/cuda_status.cc:50

Cardinality: -2 sum: AddN
I0000 00:00:1794582318.604235       1 generator_dataset_op.cc:213] Memory patch applied: M_TRIM_THRESHOLD=128 kb was set.
Epoch 1/3
4/4 - 1s - loss: 0.4239 - binary_accuracy: 0.5000 - val_loss: 1.0595 - val_binary_accuracy: 0.0000e+00 - 1s/epoch - 274ms/step
Epoch 2/3
W0000 00:00:1794582319.710607      44 op_kernel.cc:1934] OP_REQUIRES failed at variable_ops.cc:120 : ALREADY_EXISTS: Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
=== Source Location Trace: ===
tensorflow/core/framework/resource_mgr.cc:262

W0000 00:00:1794582319.710660      44 local_rendezvous.cc:461] Local rendezvous is aborting with status: ALREADY_EXISTS: Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
         [[{{node DirectSumLoss/AddN/tmp_var}}]]
=== Source Location Trace: ===
tensorflow/core/framework/resource_mgr.cc:262
tensorflow/core/common_runtime/executor.cc:1156

Traceback (most recent call last):
  File "/app/repro.py", line 82, in <module>
    main()
  File "/app/repro.py", line 78, in main
    model.fit(train, validation_data=validation, epochs=3, verbose=2)
  File "/usr/local/lib/python3.11/site-packages/tf_keras/src/utils/traceback_utils.py", line 70, in error_handler
    raise e.with_traceback(filtered_tb) from None
  File "/usr/local/lib/python3.11/site-packages/tensorflow/python/eager/execute.py", line 53, in quick_execute
    tensors = pywrap_tfe.TFE_Py_Execute(ctx._handle, device_name, op_name,
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tensorflow.python.framework.errors_impl.AlreadyExistsError: Graph execution error:

Detected at node DirectSumLoss/AddN/tmp_var defined at (most recent call last):
<stack traces unavailable>
Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
         [[{{node DirectSumLoss/AddN/tmp_var}}]] [Op:__inference_train_function_1109]
```

</details>

## What the repro isolates

- A finite `tf.data.Dataset.from_generator()` reports **unknown cardinality**; Keras probes EOF after four valid batches.
- A data-independent loss input can run before `IteratorGetNext` completes.
- The 55M-float `Empty` tensor triggers Grappler's memory scheduling threshold on CPU.
- A **3-input `tf.add_n`** becomes `TemporaryVariable` / `AssignAdd` / `DestroyTemporaryVariable`, even with arithmetic optimization disabled.
- `--known-cardinality` prevents the extra EOF-probing training call; `--stack` keeps EOF but uses `Pack + Sum` instead of `AddN`.

Previously reproduced with `TFRecordDataset.map(...).shuffle(...).batch(...).prefetch(...)` as well. A separately instrumented TF 2.18.1 C++ build showed **Create succeeds on EOF, Destroy is skipped, and the next epoch reuses the same StepContainer/ResourceMgr before Create returns `ALREADY_EXISTS`**.

**Scope:** This is a deterministic reproducer for the reported CPU configuration, not a claim about all devices or releases. The large `Empty` tensor deliberately forces the optimizer path; it is not part of the production loss.

## Optional C++ evidence

For Create/Delete and StepContainer lifecycle tracing, see [optional C++ diagnostics](diagnostics/README.md). The ordinary reproduction does **not** require building TensorFlow from source.
