#!/usr/bin/env python3
"""Instrument a CLEAN tensorflow/tensorflow v2.18.1 checkout.

No resource-management behavior is intentionally changed: only LOG(WARNING)
tracing and status-local refactoring preserving OP_REQUIRES_OK semantics.
Fails closed if upstream source anchors differ.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    hits = text.count(old)
    if hits != 1:
        raise ValueError(f"{label}: expected exactly one source anchor; found {hits}")
    return text.replace(old, new, 1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path, help="TensorFlow v2.18.1 checkout")
    args = p.parse_args()
    root = args.source
    targets: dict[str, str] = {}

    path = "tensorflow/core/kernels/variable_ops.cc"
    s = (root / path).read_text()
    s = replace_once(
        s,
        """    OP_REQUIRES_OK(context,
                   context->step_container()->Create(rm, unique_name, tmp_var));""",
        """    auto* tfres_sc = context->step_container();
    LOG(WARNING) << "TFRES CREATE_BEGIN name=" << unique_name
                 << " node=" << name() << " sc=" << tfres_sc
                 << " rm=" << rm << " ptr=" << tmp_var;
    s = tfres_sc->Create(rm, unique_name, tmp_var);
    LOG(WARNING) << "TFRES CREATE_END name=" << unique_name
                 << " sc=" << tfres_sc << " rm=" << rm
                 << " ptr=" << tmp_var
                 << " ok=" << s.ok()
                 << " code=" << static_cast<int>(s.code())
                 << " status=" << s.ToString();
    OP_REQUIRES_OK(context, s);""",
        "TemporaryVariable Create",
    )
    s = replace_once(
        s,
        """    ~TmpVar() override { VLOG(3) << "TmpVar " << name << " deleted"; }""",
        """    ~TmpVar() override {
      LOG(WARNING) << "TFRES TMPVAR_DTOR name=" << name << " ptr=" << this;
      VLOG(3) << "TmpVar " << name << " deleted";
    }""",
        "TmpVar destructor",
    )
    s = replace_once(
        s,
        """    OP_REQUIRES_OK(
        context, context->step_container()->Delete<TemporaryVariableOp::TmpVar>(
                     rm, unique_name));""",
        """    auto* tfres_sc = context->step_container();
    LOG(WARNING) << "TFRES DELETE_BEGIN name=" << unique_name
                 << " node=" << name() << " sc=" << tfres_sc
                 << " rm=" << rm;
    Status tfres_delete_status =
        tfres_sc->Delete<TemporaryVariableOp::TmpVar>(rm, unique_name);
    LOG(WARNING) << "TFRES DELETE_END name=" << unique_name
                 << " sc=" << tfres_sc << " rm=" << rm
                 << " ok=" << tfres_delete_status.ok()
                 << " code=" << static_cast<int>(tfres_delete_status.code())
                 << " status=" << tfres_delete_status.ToString();
    OP_REQUIRES_OK(context, tfres_delete_status);""",
        "TemporaryVariable Delete",
    )
    targets[path] = s

    path = "tensorflow/core/framework/resource_mgr.h"
    s = (root / path).read_text()
    s = replace_once(
        s,
        """  ~ScopedStepContainer() { CleanUp(); }""",
        """  ~ScopedStepContainer() {
    LOG(WARNING) << "TFRES SC_DTOR sc=" << this
                 << " step_id=" << step_id_ << " container=" << container_
                 << " dirty=" << dirty_.load();
    CleanUp();
  }""",
        "ScopedStepContainer destructor",
    )
    s = replace_once(
        s,
        """      cleanup_(container_);
      dirty_ = false;""",
        """      LOG(WARNING) << "TFRES SC_CLEANUP_BEGIN sc=" << this
                   << " step_id=" << step_id_ << " container=" << container_;
      cleanup_(container_);
      LOG(WARNING) << "TFRES SC_CLEANUP_END sc=" << this
                   << " step_id=" << step_id_ << " container=" << container_;
      dirty_ = false;""",
        "ScopedStepContainer cleanup",
    )
    targets[path] = s

    path = "tensorflow/core/common_runtime/eager/context.cc"
    s = (root / path).read_text()
    s = replace_once(
        s,
        """void EagerContext::StartStep() {
  mutex_lock ml(metadata_mu_);
  num_active_steps_++;
}""",
        """void EagerContext::StartStep() {
  mutex_lock ml(metadata_mu_);
  num_active_steps_++;
  LOG(WARNING) << "TFRES EAGER_START count=" << num_active_steps_.load()
               << " sc=" << step_container_.get();
}""",
        "EagerContext StartStep",
    )
    s = replace_once(
        s,
        """void EagerContext::EndStep() {
  mutex_lock ml(metadata_mu_);
  num_active_steps_--;
  if (num_active_steps_ == 0) {
    // TODO(b/139809335): This does not properly clean up remote resources
    // Clean up the previous step container and create a new one.
    step_container_ = std::make_unique<ScopedStepContainer>(
        0, [this](const string& name) { ClearResourceContainer(name); });
  }
}""",
        """void EagerContext::EndStep() {
  mutex_lock ml(metadata_mu_);
  num_active_steps_--;
  LOG(WARNING) << "TFRES EAGER_END count=" << num_active_steps_.load()
               << " sc=" << step_container_.get();
  if (num_active_steps_ == 0) {
    // TODO(b/139809335): This does not properly clean up remote resources
    // Clean up the previous step container and create a new one.
    step_container_ = std::make_unique<ScopedStepContainer>(
        0, [this](const string& name) { ClearResourceContainer(name); });
    LOG(WARNING) << "TFRES EAGER_SC_RESET sc=" << step_container_.get();
  }
}""",
        "EagerContext EndStep",
    )
    s = replace_once(
        s,
        """void EagerContext::ClearResourceContainer(const string& name) {
  // TODO(b/139809335): This does not properly clean up remote resources
  auto local_devices = local_device_mgr()->ListDevices();
  for (Device* device : local_devices) {
    // Only ignore container not found errors.
    device->resource_manager()->Cleanup(name).IgnoreError();
  }
}""",
        """void EagerContext::ClearResourceContainer(const string& name) {
  // TODO(b/139809335): This does not properly clean up remote resources
  auto local_devices = local_device_mgr()->ListDevices();
  for (Device* device : local_devices) {
    // Only ignore container not found errors.
    LOG(WARNING) << "TFRES DEVICE_CLEANUP_BEGIN container=" << name
                 << " device=" << device->name()
                 << " rm=" << device->resource_manager();
    Status tfres_status = device->resource_manager()->Cleanup(name);
    LOG(WARNING) << "TFRES DEVICE_CLEANUP_END container=" << name
                 << " device=" << device->name()
                 << " rm=" << device->resource_manager()
                 << " ok=" << tfres_status.ok()
                 << " code=" << static_cast<int>(tfres_status.code())
                 << " status=" << tfres_status.ToString();
    tfres_status.IgnoreError();
  }
}""",
        "EagerContext ClearResourceContainer",
    )
    targets[path] = s

    path = "tensorflow/core/common_runtime/eager/kernel_and_device.cc"
    s = (root / path).read_text()
    s = replace_once(
        s,
        """  opts->step_container = step_container;
  opts->collective_executor =""",
        """  opts->step_container = step_container;
  LOG(WARNING) << "TFRES FUNCTION_RUN_OPTIONS sc=" << step_container
               << " step_id=" << opts->step_id;
  opts->collective_executor =""",
        "KernelAndDeviceFunc PrepareForRun",
    )
    targets[path] = s

    path = "tensorflow/core/kernels/partitioned_function_ops.cc"
    s = (root / path).read_text()
    s = replace_once(
        s,
        """  run_opts.step_container = step_container;
  run_opts.cancellation_manager =""",
        """  run_opts.step_container = step_container;
  LOG(WARNING) << "TFRES PART_CALL_BEGIN sc=" << step_container
               << " step_id=" << run_opts.step_id
               << " function=" << func_->name();
  run_opts.cancellation_manager =""",
        "PartitionedCall RunFunction",
    )
    s = replace_once(
        s,
        """             delete rets;
             delete step_container;
             done();""",
        """             delete rets;
             LOG(WARNING) << "TFRES PART_CALL_END sc=" << step_container
                          << " ok=" << status.ok()
                          << " code=" << static_cast<int>(status.code());
             delete step_container;
             done();""",
        "PartitionedCall callback cleanup",
    )
    targets[path] = s

    # Fail closed / all or nothing: write only after every anchor matches.
    for file, data in targets.items():
        (root / file).write_text(data)
        print("PATCHED", file)
    (root / "tfres_patch_manifest.json").write_text(
        json.dumps(
            {
                "tensorflow_tag": "v2.18.1",
                "files": list(targets),
                "instrumentation_prefix": "TFRES",
                "note": "Logging-only patches",
            },
            indent=2,
        )
    )
    print("PATCH_OK", len(targets), "files")


if __name__ == "__main__":
    main()
