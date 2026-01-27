# Obtain requirements of the notebook

To obtain the requirements of your Jupyter notebook, you have can do it automatically following [Option 1](#option-1-automated-extraction-of-requirements) or manually following [Option 2 ](#option-2-manual-extraction-of-requirements).

If you already have a versioned `requirements.txt` we recommend you to follow [Option 2](#option-2-manual-extraction-of-requirements) as it will be faster. Otherwise, please follow [Option 1](#option-1-automated-extraction-of-requirements).

## Option 1: Automated extraction of requirements

> **IMPORTANT**: This option requires you to have a Python environment where your notebook can run without errors. This environment can be a local Conda/VirtualEnv or an online Google Colab session.

### 1. 


## Option 2: Manual extraction of requirements

You would need to create a `requirements.yaml` file similar to the [example requirements.yaml file](../templates/requirements.yaml). This file should contain 3 different fields:
- **dependencies**: A list of all the packages used in the notebook along with their versions (e.g., `pandas==2.2.2`). The list needs to be indexed with a hyphen (`- `) followed by a space before each package as in the example.
- **python_version**: The version of Python used in the notebook (e.g., `3.11.1`).
- **description**: A short desctiption of the notebook and its purpose.