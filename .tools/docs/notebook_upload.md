# Considerations for Uploading Notebooks

When uploading Jupyter notebooks to a documentation site or repository, consider the following best practices to ensure clarity, accessibility, and maintainability:

## 1. File naming conventions
- Use descriptive and consistent file names that reflect the content of the notebook.
- Avoid spaces and special characters; use underscores or hyphens instead (e.g., `data_analysis.ipynb`).

## 2. Meaningful requirements file

- Ensure that the `requirements.txt` file accurately lists all necessary dependencies for the notebook to run.
- Specify exact versions of packages to ensure reproducibility (e.g., `numpy==1.21.0`).

Sometimes is hard to find the exact version of the packages you are using. For that reason, here it goes a snipet of code that can help you. Please, create a 

```bash