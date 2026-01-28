# Adding External Code

If you want to use your own Python modules or scripts in Jupyter notebooks, follow these steps to upload them easily.

## 1. Prepare your external code

Organize your external code and follow Python packaging best practices. Set up the right folder structure, add an `__init__.py` file if needed, and list any required dependencies.

**Suggested Directory Structure:**

```
src
├── __init__.py
├── my_script.py
├── subpackage/
│   ├── __init__.py
│   └── submodule1.py
```

## 2. Upload your external code to the repository

Go to the src folder in your repository and upload your files or folders there.

![Upload external code GIF](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/Upload_src.gif)

## 3. How to import into your notebook

Once uploaded, your external code will be available to your notebooks as a package. To use it, import it as shown in the examples below:

**Import the whole package:**
```python  
import PYTHON_PROJ_NAME
```

**Import function:**
```python  
from PYTHON_PROJ_NAME import my_script
```

**Import submodule:**
```python  
from PYTHON_PROJ_NAME import subpackage
```

---

<div align="center">

[← Previous](initialise_repository.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[🏠 Home](README.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[Next →](notebook_requirements.md)


</div>
