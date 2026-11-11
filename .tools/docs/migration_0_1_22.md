# Template 0.1.22: TensorFlow apps install on Windows computers with an NVIDIA GPU

Design note for the 0.1.22 migration (`.template_sync/migrations/v0_1_21_to_v0_1_22.py`). How a change reaches an installed copy is described in [migration_0_1_16.md](migration_0_1_16.md): a new installer is needed, nothing edits an existing install.

## 1. The problems

### 1.1 Windows + NVIDIA GPU: the installation of a TensorFlow app fails

`post_install.bat` installs `requirements_gpu.txt` (its lock file) when it finds `nvidia-smi`. `merge_requirements.py` wrote that file by rewriting `tensorflow` to `tensorflow[and-cuda]` for every system.

* TensorFlow's `and-cuda` extra lists `nvidia-*` packages with **no platform marker**.
* Some of them exist only as Linux wheels: `nvidia-nccl-cu12` has never had a Windows or macOS wheel, and the newest `nvidia-cublas-cu12` (12.9.3.13) is Linux-only.
* `lock_requirements.py` locks with `uv pip compile --universal`, which pins them for every system.
* On Windows, `pip install -r requirements_gpu.lock.txt` then stops with `No matching distribution found for nvidia-...`, and the installer ends with "Application requirements installation failed".

TensorFlow has had no native Windows GPU build since 2.10, so `[and-cuda]` never helped on Windows anyway. macOS was not affected: `post_install.sh` always installs the CPU file there.

Found while planning a StarDist 2D (TensorFlow 2.20) app. Reproduced with uv 0.13 for `x86_64-pc-windows-msvc`:

| Lock file | Result |
|---|---|
| 0.1.21 GPU lock | `No solution found` |
| 0.1.22 GPU lock | installs (106 packages, no `nvidia-*`) |

On Linux the 0.1.22 lock still installs `tensorflow` with the CUDA packages (119 packages).

### 1.2 The version cell always says "not listed" on Colab

The snippet in [notebook_upload.md](notebook_upload.md) did `config.get(notebook_name, "")` on `notebooks/notebook_latest_versions.yaml`. `sync_notebook_versions.py` writes that file grouped by folder (`"<folder>": {"<notebook>": "<version>"}`), so the lookup always returned `""`.

## 2. What changes

| Part | Change |
|---|---|
| `.tools/python/merge_requirements.py` | In the GPU file, each `tensorflow` line becomes two lines: `tensorflow[and-cuda]==X ; sys_platform == "linux"` and `tensorflow==X ; sys_platform != "linux"`. A line's own marker is kept and combined with `and`. uv then marks every `nvidia-*` package `sys_platform == 'linux'`. |
| `.tools/docs/notebook_upload.md` | The version cell looks the notebook up inside its folder group. |
| `.tools/docs/notebook_requirements.md` | One paragraph on what the GPU file does for TensorFlow. |

## 3. What the migration does

* **merge_requirements.py:**
  * The new function is inserted before the known 0.1.21 `build_gpu_lines`.
  * The tensorflow branch of `build_gpu_lines` is replaced.
  * The module docstring sentence is updated when it is still the 0.1.21 text.
  * The two code changes are made together or not at all.
  * A file that already has `tensorflow_gpu_lines` is `unchanged`.
  * A customised file is `SKIPPED`; apply section 2 by hand.
* **notebook_upload.md:** the one known lookup line is replaced; a customised file is `SKIPPED`.
* **Missing files** are not created. Line endings are kept.
* **Notebooks are not edited.** A notebook that already contains the old snippet keeps it. Replace the line `latest_version = config.get(notebook_name, "")` in its version cell with the two lines from [notebook_upload.md](notebook_upload.md).

## 4. Adopting it

1. Take this template version (the synchronization pull request).
2. Regenerate the GPU lock: push a notebook change, or run **Actions > Updates on notebook change > Run workflow**.
3. Build and release a new installer.

An installer made with an older template still fails on Windows computers with an NVIDIA GPU. A workaround for those users: rename or hide `nvidia-smi.exe` during the installation, so that the CPU file is used.

## 5. What is not verified here

* The template tests check:
  * the new GPU lines;
  * the migration on the 0.1.21 files (LF and CRLF);
  * idempotence;
  * customised files;
  * the chain from older versions.
* The lock results above come from uv's resolver for each platform (`uv pip install --dry-run --python-platform ...`), not from an installer run on a Windows computer with an NVIDIA GPU.
