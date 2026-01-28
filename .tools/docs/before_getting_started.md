# 📋 Before Getting Started with LabConstrictor

Welcome to LabConstrictor! This guide will help you understand the [basics of LabConstrictor](#labconstrictor-in-a-nutshell) and the [requirements](#labconstrictor-requirements) for using it effectively.

## 🎯 LabConstrictor in a Nutshell

LabConstrictor is a template repository that allows you to package Jupyter notebooks into installable desktop applications. It handles everything automatically, allowing you to follow the entire process without dealing with terminal commands or complex configurations. Here are the key features of LabConstrictor:

### ⚙️ Easy Configuration

LabConstrictor includes a web form to easily configure your repository, brand your application, and upload or update your notebooks and their dependencies.

### 🖥️ Cross-Platform Installers

Automatic workflows build installers for Windows (`.exe`), macOS (`.pkg`), and Linux (`.sh`), making it easy for users on different platforms to install and run your notebooks.

### 📦 Environment Management

LabConstrictor uses `requirements.yaml` files to manage dependencies. Automatic workflows ensure your notebooks run in a consistent environment across different systems. LabConstrictor also includes helper notebooks for generating and validating requirement files.

### 📈 Version Control

LabConstrictor includes helper cells that track notebook versions and alert users when updates are available, ensuring they always have access to the latest features and fixes.

### ✨ User-Friendly Experience

Installers handle the setup process, allowing users to launch your notebooks with a simple desktop application. The app displays a Welcome Dashboard where users can check versions and select notebooks easily. Notebooks feature hidden code with a play button to run cells, providing a clean, app-like interface.

### 🔒 Repository Privacy

LabConstrictor lets you control your repository as private or public, giving you full control over who can access and use your notebooks.

### 📱 Offline Usage

As long as your notebooks don't require internet access, users can run the desktop applications offline after installation.

## ✅ LabConstrictor Requirements

To use LabConstrictor effectively, please ensure you meet the following requirements:

- **🐙 GitHub Account:** You will need a GitHub account to create a new repository from the LabConstrictor template.
- **📓 Jupyter Notebooks:** Have your Jupyter notebooks ready that you want to package into desktop applications.
- **🐍 Python Environment:** A Python environment (local or online) where your notebooks can run without errors. This is necessary for generating and validating requirement files.


---

<div align="center">

← Previous &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[🏠 Home](README.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[Next →](create_repository.md)

</div>