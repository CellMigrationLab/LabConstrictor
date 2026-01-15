# LabConstrictor

LabConstrictor is a GitHub repository template provided with automated workflows to help you build and distribute your Jupyter notebook-based applications across multiple platforms. You would just need to upload your notebooks and requirements and the workflows will take care of the rest! You will get a ready-to-use installer for Windows, macOS, and Linux with every new release you create.

## How to Use?

### Step 1: Create a New Repository from this Template

Click the "Use this template" button at the top of this page to create a new repository based on the LabConstrictor template.

### Step 2: Customize Your Application

Go to https://labconstrictor-form.streamlit.app/ and fill out the form with your application's details. At the end of the form, put your newly created repository's URL. Submit the form to automatically generate the necessary files, this will create a Pull Request in your repository, accept it and merge it. 

> IMPORTANT: These instructions will be moved to [.tools/docs](.tools/docs) once the Pull Request is merged. A link to them will be added to the repository's README.md file for future reference, so don't be afraid of losing them!

### Step 3: Add Your Notebooks and Requirements

Add your Jupyter notebooks together with their requirements files, follow the instructions in [Do you want to upload a notebook?](.tools/docs/notebook_upload.md) to ensure a smooth upload process.

### Step 4: Create Executable Installers
To build installers for Windows, macOS, and Linux, you need to create a new release in your repository. Follow the instructions in [Do you want to create an installer executable file with your notebooks?](.tools/docs/executable_creation.md) to create a release and generate the installers.