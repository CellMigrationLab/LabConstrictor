# LabConstrictor

LabConstrictor is a GitHub repository template provided with automated workflows to help you build and distribute your Jupyter notebook-based applications across multiple platforms. You would just need to upload your notebooks and requirements and the workflows will take care of the rest! You will get a ready-to-use installer for Windows, macOS, and Linux with every new release you create.

## How to Use?

### Step 1: Create a New Repository from this Template

Click the "Use this template" button at the top of this page to create a new repository based on the LabConstrictor template.

### Step 2: Customize Your Application

Go to https://labconstrictor-form.streamlit.app/ and fill out the form with your application's details. At the end of the form, put your newly created repository's URL. Submit the form to automatically generate the necessary files, this will create a Pull Request in your repository, accept it and merge it. 

> IMPORTANT: This instructions will be moved to [.tools/docs](.tools/docs) once the Pull Request is mergec. A link to them will be added to the repository's README.md file for future reference, so don't be afraid of losing them!

### Step 3: Add Your Notebooks and Requirements

Add your Jupyter notebooks together with a `requirements.txt` file listing all the Python packages your application needs to the `notebooks` directory in your repository.

#### Important Notes
- To ensure reproducibility, it's recommended to specify exact package versions in your `requirements.txt` file (e.g., `numpy==1.21.0`).
- Both the `Jupyter notebook` and the `requirements.txt` must be placed in a folder when including to the `notebooks` directory.
- LabConstrictor provides a versioning system. In order to benefit from it, on the updated notebook specify the version number in a cell as follows:
  ```python
  current_version = "1.0.0"
  ```

### Step 4: Create a New Release
Create a new release in your repository by going to the "Releases" section and clicking on "Draft a new release". Create a tag for your release (e.g., `v1.0.0`) and publish the release. The GitHub Actions workflows will automatically build installers for Windows, macOS, and Linux, and attach them to the release.