# Write Notebooks That Run Well in Both Google Colab and JupyterLab

LabConstrictor ships notebooks as desktop apps built on JupyterLab. At the same time, many collaborators and reviewers prefer Google Colab for quick, cloud-based runs. Writing your notebook to work in both environments makes it easier for users to:

- **Choose their preferred platform** (Colab in the browser, JupyterLab locally or inside LabConstrictor).
- **Collaborate and review quickly** without forcing everyone to install dependencies.
- **Reproduce results** across cloud and local setups, reducing “works on my machine” issues.
- **Avoid hidden environment assumptions** that only exist in one runtime.

Below are practical patterns to keep notebooks portable and readable across both runtimes.

---

## 1. Keep explanatory text visible when code is hidden

LabConstrictor apps often hide code cells to present an app-like UI. If you use `#@title` headers in Colab, place them **at the top of the cell** so they remain visible in JupyterLab and when code is collapsed or hidden in LabConstrictor.

**Good pattern (title at top of the cell):**

```python
#@title Data input
# Rest of the cell...
```

When you need longer explanations, prefer **Markdown cells** so the text is visible everywhere, regardless of code visibility.

---

## 2. Guard Colab-only setup code

Colab-specific setup (mounting Google Drive, installing GPU-only deps, `!pip` installs) should run **only** on Colab. Wrap it like this:

```python
import sys

if 'google.colab' in sys.modules:
    print("🚀 Detected Google Colab. Starting installation...")

    !pip install -q "cellpose[all]" tifffile
    !pip install -q instanseg-torch

    from google.colab import userdata
    from google.colab import drive

    drive.mount('/content/gdrive')

    print("✅ Colab setup done")
else:
    # Fallback for local environments
    print("done")
```

This keeps local JupyterLab and LabConstrictor runs clean and predictable.

---

## 3. Prefer cross-platform paths and storage

- Use `pathlib.Path` and **relative paths** when possible.
- Avoid hard-coding Colab paths like `/content` or `/content/gdrive` outside guarded blocks.
- For data files, include a **config cell** where users can set a local path or select a file.

---

## 4. Minimize environment-specific dependencies

- Keep the core notebook runnable with standard, pip-installable dependencies.
- If you need GPU-only or system-level packages, **isolate them** in guarded cells and provide a fallback or clear message.
- Pin critical versions to avoid “works in Colab but not locally” conflicts.

---

## 5. Avoid Colab-only UI helpers

Some Colab widgets and `google.colab` utilities won’t run in JupyterLab. Prefer:

- Standard ipywidgets where possible.
- Plain input prompts or config dictionaries.
- Lightweight, backend-agnostic plotting (Matplotlib, Plotly, etc.).

---

## 6. Clearly label runtime-specific instructions

Add small callouts in Markdown to guide the user, for example:

> **Colab users:** Run the “Colab setup” cell first to mount Google Drive.
>
> **JupyterLab users:** Skip the Colab setup cell and configure the local data path instead.

This reduces confusion and keeps the flow smooth in both environments.

---

## 7. Keep the first cells lightweight

In both Colab and LabConstrictor, notebooks feel faster if the first cells are quick to run. Put heavy installs or downloads behind a **dedicated setup cell** and provide progress messages.

---

## 8. Test in both environments before release

Before uploading to LabConstrictor:

1. Run the notebook end-to-end in **JupyterLab** (or local Jupyter) to validate the LabConstrictor experience.
2. Run the same notebook in **Google Colab** to confirm cloud compatibility.

Testing both early prevents surprises for your users later.

---

<div align="center">

[← Previous](notebook_upload.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
[🏠 Home](README.md)

</div>
