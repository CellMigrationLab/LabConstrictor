# LabConstrictor

LabConstrictor is a template for you to create your own GitHub repository so that you can upload your notebook and wrap them on executable installers for users to easily set up and use your notebooks.

## Who is this for?

Do you have Jupyter notebooks and you want to distribute them so that users do not need to deal with Python dependencies? Then LabConstrictor is for you. 

## What do you need?

You just need to have a Jupyter notebook that is currently working on an environment (e.g. cvonda, virtualenv or Google Colab) and a GitHub account. If you have these two requirements, by following the [Quick start guidelines](#quick-start) you will be able to start using LabConstrictor. 

## What do you get?

LabConstrictor is provided with automated processes that take care of validation, executable creation, etc. These processes will help you as a developer to deploy your notebooks smoothly and ensure that the users are able to use the notebooks in the same way as you developed it.

# Quick start

### Step 1: Create a New Repository from this Template

Click the `Use this template` button at the top of this page to create a new repository based on the LabConstrictor template.

![Use template screenshot](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/Use_Template.png)

To create a new repository you will need to provide:

1. **General**:
    - Choose the **Owner** of the repository (e.g. your GitHub account or your research group GitHub organisation).
    - Choose a **Repository name** that is short and memorable.
    - [Optional] Give a short description to the repository where you describe what are your notebooks for.
2. **Configuration**: 
    - Choose the **Visibility** of your repository:
        - **Public** if you already want people to start using it.
        - **Private** if you want to keep it for your organisation or you are still developing your notebooks.

Then, click on `Create repository` and your respository ahs been created!

### Step 2: Initialiae your repository

Now that you have your repository, you are ready to initialise and customise it. For that, please go to https://labconstrictor-form.streamlit.app/ and click `Start initialisation` on the **Initialise a repository** section. Then, follow the provided guidelines on the website and once you have submited the form a Pull Request (suggested contributions) will be created on your repository, follow the steps on the GIF bellow to accept those suggestions:

![Accept a Pull Request GIF](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/Accept_PR.gif)

> **IMPORTANT**: Once the suggestions are accepted, these instructions will be moved to [.tools/docs](.tools/docs). A link to them will be remain for future reference, so don't be afraid of losing them!

### Step 3: Add Your Notebooks and Requirements

Add your Jupyter notebooks together with their requirements files, follow the instructions in [Do you want to upload a notebook?](.tools/docs/notebook_upload.md) to ensure a smooth upload process.

### Step 4: Create Executable Installers

To build installers for Windows, macOS, and Linux, you need to create a new release in your repository. Follow the instructions in [Do you want to create an installer executable file with your notebooks?](.tools/docs/executable_creation.md) to create a release and generate the installers.
