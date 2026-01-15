# Do you want to use external code in your notebooks?

If you have external code (e.g., Python modules or scripts) that you would like to use in your Jupyter notebooks, please follow the guidelines below to ensure a smooth upload process.

## 1. Prepare your external code

Make sure that your external code is well-organized and follows best practices for Python packaging. This includes having an appropriate directory structure, including an `__init__.py` file if necessary, and ensuring that any dependencies are clearly defined.

## 2. Upload your external code to the repository

You need to upload the external code to the `src` directory in your repository. Please follow the steps on the GIF below to upload your external code:

![Upload external code GIF](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/Upload_src.gif)

## Important consideration

Your external code will be made accesible to your notebooks as a package. Therefore, in order to use the external code on your notebooks, it you will need to be imported similar to the example below:

```python  
import PYTHON_PROJ_NAME
```

or 

```python  
from PYTHON_PROJ_NAME import your_function_name
```