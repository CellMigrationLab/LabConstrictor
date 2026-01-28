# Adding External Code

If you have external code (e.g., Python modules or scripts) that you would like to use in your Jupyter notebooks, please follow the guidelines below to ensure a smooth upload process.

## 1. Prepare your external code

Make sure that your external code is well-organized and follows best practices for Python packaging. This includes having an appropriate directory structure, including an `__init__.py` file if necessary, and ensuring that any dependencies are clearly defined.

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

Navigate to the src folder in your repository and upload your files or folders there.

![Upload external code GIF](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/Upload_src.gif)

## 3. How to import in your notebook

Your external code will be made accesible to your notebooks as a package. Therefore, in order to use the external code on your notebooks, it you will need to be imported similar to the example below:

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