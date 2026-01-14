# Do you want to use custom code in your notebooks?

If you have custom code (e.g., Python modules or scripts) that you would like to use in your Jupyter notebooks, you can easily upload it to the `src`directory in your repository. By doing this, our automated workflows will ensure that your custom code is properly installed and available for use in your notebooks.

## Important consideration

Your custom code will be made accesible to your notebooks installed as a package. Therefore, in order to use it you will need to import it similar to the example below:

```python  
import PYTHON_PROJ_NAME
```

or 

```python  
from PYTHON_PROJ_NAME import your_function_name
```