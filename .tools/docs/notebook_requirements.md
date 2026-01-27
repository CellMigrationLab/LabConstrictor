# Obtain requirements of the notebook

To obtain the requirements of your Jupyter notebook, you have can do it automatically following [Option 1](#option-1-automated-extraction-of-requirements) or manually following [Option 2 ](#option-2-manual-extraction-of-requirements).

If you already have a versioned `requirements.txt` we recommend you to follow [Option 2](#option-2-manual-extraction-of-requirements) as it will be faster. Otherwise, please follow [Option 1](#option-1-automated-extraction-of-requirements).

## Option 1: Automated extraction of requirements

> **IMPORTANT**: This option requires you to have a Python environment where your notebook can run without errors. This environment can be a local Conda/VirtualEnv or an online Google Colab session.

### 1. Open the requirements generator notebook

You have two options to open the requirements generator notebook:
 - **Locally**: Download the [Requirements_Generator.ipynb](https://raw.githubusercontent.com/CellMigrationLab/LabConstrictor/main/.tools/notebooks/Requirements_Generator.ipynb) and open it in your local Python environment (conda or virtualenv).
  > **Note**: The Python environment where you open the requirements generator notebook needs to be the one you use to run the target notebook whose requirements you want to extract.
 - **Google Colab**: Open the notebook directly in Google Colab by clicking [here](https://colab.research.google.com/github/CellMigrationLab/LabConstrictor/blob/main/.tools/notebooks/Requirements_Generator.ipynb).

### 2. Run the requirements generator notebook

In the requirements generator notebook, follow the instructions provided in the notebook to generate the `requirements.yaml` file for the Jupyter notebook you want to extract requirements from. You will need to provide the path to your notebook file when prompted.

## Option 2: Manual extraction of requirements

### 1. Create a requirements.yaml file

You would need to create a `requirements.yaml` file similar to the [example requirements.yaml file](../templates/requirements.yaml). This file should contain 3 different fields:
- **dependencies**: A list of all the packages used in the notebook along with their versions (e.g., `pandas==2.2.2`). The list needs to be indexed with a hyphen (`- `) followed by a space before each package as in the example.
- **python_version**: The version of Python used in the notebook (e.g., `3.11.1`).
- **description**: A short desctiption of the notebook and its purpose.

### 2. Open the requirements validator notebook

You have two options to open the requirements generator notebook, but in this case we recommend using Google Colab as you don't need any specific Python environment to run the validator. Still, here are the two options:

- **Local**: Download the [Requirements_Validator.ipynb](https://raw.githubusercontent.com/CellMigrationLab/LabConstrictor/main/.tools/notebooks/Requirements_Validator.ipynb) and open it in any Python environment with ipywidgets installed.
- **Google Colab**: Open the notebook directly in Google Colab by clicking [here](https://colab.research.google.com/github/CellMigrationLab/LabConstrictor/blob/main/.tools/notebooks/Requirements_Validator.ipynb).

### 3. Run the requirements validator notebook

In the requirements validator notebook, follow the instructions provided in the notebook to validate your `requirements.yaml` file. You will need to provide the path to your `requirements.yaml` file when prompted.