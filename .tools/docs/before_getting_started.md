# Before Getting Started with LabConstrictor

Welcome to LabConstrictor! This guide will help you understand the [basics of LabConstrictor](#labconstrictor-in-a-nutshell) and the [requirements](#labchronicle-requirements) for using it effectively.

## LabConstrictor in a Nutshell

LabConstrictor is a template repository that allows you to package Jupyter notebooks into installable desktop applications. It does this atomaticaly, allowing you to follow the whole process without needing to deal with any terminal commands or complex configurations. Here are the mean features of LabConstrictor:

### Easy Configuration

LabConstrictor includes a web form to easily configure your repository, brand your application, and upload or update your notebooks and their requirements into the repository.

### Cross-Platform Installers

Automatic workflows build installers for Windows (`.exe`), macOS (`.pkg`), and Linux (`.sh`), making it easy for users on different platforms to install and run your notebooks.

### Environment Management

LabConstrictor uses `requirements.yaml` files to manage dependencies, by using automatic workflows you will ensure that your notebooks run in a consistent environment across different systems. LabConstrictor also includes notebooks for generating and validating these requirements files.

### Version Control

LabConstrictor includes helper cells that track the version of your notebooks and alert users when an update is available, ensuring they always have access to the latest features and fixes.

### User-Friendly Experience

Installers will take care of the setup process, allowing users to launch your notebooks with a simple desktop application. The desktop application will launch a Welcome Dashboard, from where users can easily check the versioning of your notebook and choose your notebooks easily. Your notebooks would also have the code hidden and a play button to run the cells, providing a clean and user-friendly interface.

### Repository Privacy

LabConstrictor allows you to handle your repository privately or publicly, giving you control over who can access and use your notebooks.

### Offline Usage

As long as your notebooks do not require internet access for their functionality, users will be able to use the desktop applications offline after installation.

## LabChronicle requirements

To use LabConstrictor effectively, please ensure that you meet the following requirements:

- **GitHub Account:** You will need a GitHub account to create a new repository from the LabConstrictor template.
- **Jupyter Notebooks:** Have your Jupyter notebooks ready that you want to package into desktop applications.
- **Python Environment:** A Python environment (local or online) where your notebooks can run without errors. This is necessary for generating and validating requirements files.


---

<div align="center">

← Previous &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[🏠 Home](README.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[Next →](create_repository.md)

</div>