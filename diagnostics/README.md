# Optional: C++ resource-lifecycle trace

**Not needed to reproduce the bug.** The root README takes three Docker commands and uses official wheels. This folder is for maintainers who want to confirm the resource leak with C++ logs.

From the repository root (Linux x86-64 / WSL2 Docker):

```bash
BAZEL_JOBS=4 ./diagnostics/build.sh   # builds TensorFlow v2.18.1 from source
./diagnostics/run.sh                  # failure + 2 successful controls
```

<details>

<summary>Observed output</summary>

```log
==== bad_addn_unknown (expected: ALREADY_EXISTS) ====
EOF messages: 1
CREATE_END_OK: 5
DELETE_END_OK: 4
CREATE_END_FAIL: 1
Eager EndStep: 0 StepContainer cleanup: 0
RESOURCE name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 create_ok=5 delete_ok=4 create_failed=1
COLLISION at L352: prior CREATE_OK at L274; matching Delete after Create=False, matching StepContainer cleanup=False
NOTE: TMPVAR_DTOR is not proof of Delete: a failed Create also destructs its new object.
Exit code: 1; observed: ALREADY_EXISTS
==== known_cardinality (expected: PASS) ====
EOF messages: 0
CREATE_END_OK: 12
DELETE_END_OK: 12
CREATE_END_FAIL: 0
Eager EndStep: 0 StepContainer cleanup: 0
RESOURCE name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x6455a12f4680 rm=0x6455a12d2d00 create_ok=12 delete_ok=12 create_failed=0
NOTE: TMPVAR_DTOR is not proof of Delete: a failed Create also destructs its new object.
Exit code: 0; observed: PASS
==== stack_sum (expected: PASS) ====
EOF messages: 1
CREATE_END_OK: 0
DELETE_END_OK: 0
CREATE_END_FAIL: 0
Eager EndStep: 0 StepContainer cleanup: 0
NOTE: TMPVAR_DTOR is not proof of Delete: a failed Create also destructs its new object.
Exit code: 0; observed: PASS

Logs and summaries: /mnt/workspace/tensorflow-temporary-variable-eof-repro/diagnostics/results
```

</details>

The same **root `repro.py`** runs in both the official-wheel and instrumented-wheel containers. `run.sh` bind-mounts it at runtime. It records `diagnostics/results/{bad_addn_unknown,known_cardinality,stack_sum}/{run.log,summary.txt}`; do **not** commit `diagnostics/results/`.

The patcher adds `TFRES` logging to `TemporaryVariable` Create/Delete/destructor, `ScopedStepContainer` cleanup/destructor, `EagerContext` StartStep/EndStep, and function execution container forwarding. It does not intentionally alter cleanup behavior. Source anchors are strictly checked for tag **v2.18.1**; compilation stops if they differ. Build uses pinned Bazel 6.5.0 via Bazelisk and Clang 17, CPU-only. Recommended resources: **24+ GiB RAM**, **50+ GiB free disk**; try `BAZEL_JOBS=2 BAZEL_RAM_MB=8192 ./diagnostics/build.sh` if RAM is tight.

In an earlier run using the more elaborate diagnostic reproducer on TF 2.18.1, the failing case produced **5 successful Create calls, 4 successful Delete calls, and 1 `ALREADY_EXISTS` Create failure**. A successful known-cardinality case produced **12 Create / 12 Delete**, and a `Pack + Sum` case created **zero** temporary resources. This public minimal version has not yet been tested with the instrumented build; reproduce and compare `summary.txt` before relying on the counts.

To inspect the event sequence:

```bash
grep -E 'TFRES (CREATE|DELETE|SC_CLEANUP|EAGER_END)' diagnostics/results/bad_addn_unknown/run.log | tail -n 50
```

<details>

<summary>Observed output</summary>

```log
2026-11-13 14:04:48.531251: W tensorflow/core/kernels/variable_ops.cc:119] TFRES CREATE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN/tmp_var sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x7611fc001360
2026-11-13 14:04:48.531294: W tensorflow/core/kernels/variable_ops.cc:123] TFRES CREATE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x7611fc001360 ok=1 code=0 status=OK
2026-11-13 14:04:48.586652: W tensorflow/core/kernels/variable_ops.cc:178] TFRES DELETE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN sc=0x5e93f99f6b40 rm=0x5e93f7117a30
2026-11-13 14:04:48.586724: W tensorflow/core/kernels/variable_ops.cc:183] TFRES DELETE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ok=1 code=0 status=OK
2026-11-13 14:04:48.588369: W tensorflow/core/kernels/variable_ops.cc:119] TFRES CREATE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN/tmp_var sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761200001c80
2026-11-13 14:04:48.588429: W tensorflow/core/kernels/variable_ops.cc:123] TFRES CREATE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761200001c80 ok=1 code=0 status=OK
2026-11-13 14:04:48.593691: W tensorflow/core/kernels/variable_ops.cc:178] TFRES DELETE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN sc=0x5e93f99f6b40 rm=0x5e93f7117a30
2026-11-13 14:04:48.593738: W tensorflow/core/kernels/variable_ops.cc:183] TFRES DELETE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ok=1 code=0 status=OK
2026-11-13 14:04:48.595808: W tensorflow/core/kernels/variable_ops.cc:119] TFRES CREATE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN/tmp_var sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761208001500
2026-11-13 14:04:48.595900: W tensorflow/core/kernels/variable_ops.cc:123] TFRES CREATE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761208001500 ok=1 code=0 status=OK
2026-11-13 14:04:48.604300: W tensorflow/core/kernels/variable_ops.cc:178] TFRES DELETE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN sc=0x5e93f99f6b40 rm=0x5e93f7117a30
2026-11-13 14:04:48.604514: W tensorflow/core/kernels/variable_ops.cc:183] TFRES DELETE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ok=1 code=0 status=OK
2026-11-13 14:04:48.606434: W tensorflow/core/kernels/variable_ops.cc:119] TFRES CREATE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN/tmp_var sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761200001c80
2026-11-13 14:04:48.606525: W tensorflow/core/kernels/variable_ops.cc:123] TFRES CREATE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761200001c80 ok=1 code=0 status=OK
2026-11-13 14:04:48.618529: W tensorflow/core/kernels/variable_ops.cc:178] TFRES DELETE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN sc=0x5e93f99f6b40 rm=0x5e93f7117a30
2026-11-13 14:04:48.618567: W tensorflow/core/kernels/variable_ops.cc:183] TFRES DELETE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ok=1 code=0 status=OK
2026-11-13 14:04:48.619839: W tensorflow/core/kernels/variable_ops.cc:119] TFRES CREATE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN/tmp_var sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x7612140025c0
2026-11-13 14:04:48.619862: W tensorflow/core/kernels/variable_ops.cc:123] TFRES CREATE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x7612140025c0 ok=1 code=0 status=OK
2026-11-13 14:04:49.244783: W tensorflow/core/kernels/variable_ops.cc:119] TFRES CREATE_BEGIN name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 node=DirectSumLoss/AddN/tmp_var sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761214012a30
2026-11-13 14:04:49.244842: W tensorflow/core/kernels/variable_ops.cc:123] TFRES CREATE_END name=DirectSumLoss/AddN/tmp_var/frame:0/iter:0 sc=0x5e93f99f6b40 rm=0x5e93f7117a30 ptr=0x761214012a30 ok=0 code=6 status=ALREADY_EXISTS: Resource __per_step_0/DirectSumLoss/AddN/tmp_var/frame:0/iter:0/N10tensorflow19TemporaryVariableOp6TmpVarE
```

</details>

Pay attention to **resource name + `sc` (StepContainer address) + `rm` (ResourceMgr address)**. A `TMPVAR_DTOR` can belong to the newly allocated object whose Create failed, so object destructor counts alone are **not** proof that the old resource was deleted. Correlate `CREATE_END ok=1`, `DELETE_END ok=1`, `SC_CLEANUP`, and later `CREATE_END ok=0 code=6`.

The tagged upstream sources are Apache-2.0 licensed. The experimental patch is **logging-only**, not a proposed fix. Official-wheel reproduction has also been observed with TF **2.21.0**, but this particular source patch is deliberately pinned to **2.18.1**, the version previously compiled and traced successfully.
