# LabConstrictor
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20758747.svg)](https://doi.org/10.5281/zenodo.20758747)

![LabConstrictor Comic](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/comic.png)

**LabConstrictor turns your Jupyter notebooks into desktop apps that anyone can install.** Your users download an installer, double-click, and work. They need no Python, no pip and no terminal.

This repository is a GitHub template. You bring the notebooks; it builds the installers for Windows, macOS and Linux, and gives the app a Welcome page that lists your notebooks.

**Website, guides and ready-made apps: <https://cellmigrationlab.github.io/LabConstrictor-Site/>**

## Who is it for?

- **Researchers** who want colleagues to run an analysis without setting up Python.
- **Developers** who ship interactive notebooks to people who do not code.
- **Teachers** who want a workshop to start with a double-click.

Looking for an app to use, not to build? Go to the [App Centre](https://cellmigrationlab.github.io/LabConstrictor-Site/apps/).

## What your users get

![An installed LabConstrictor app: installer, Welcome notebook and a notebook with hidden code](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/Summary.gif)

- An installer for their system: `.exe` (Windows), `.pkg` (macOS) or `.sh` (Linux).
- A Welcome notebook that opens in the browser and lists the app's notebooks.
- Notebooks with the code hidden, so they look like an app. The code can be shown again.
- A notice when a newer version of the app is available.

## Quick start

You need a GitHub account and the notebooks you want to share. Read [Before getting started](.tools/docs/before_getting_started.md) first, then:

1. [Create a new repository from this template](.tools/docs/create_repository.md)
2. [Enable automatic template updates](.tools/docs/template_synchronization.md)
3. [Initialise your repository](.tools/docs/initialise_repository.md) with the web form
4. [Upload external code](.tools/docs/external_code_upload.md) (optional)
5. [Upload your notebooks](.tools/docs/notebook_upload.md)
6. [Create the installers](.tools/docs/executable_creation.md)

The same guides, with pictures and a search box, are on the [website](https://cellmigrationlab.github.io/LabConstrictor-Site/build/).

## Go further

- [List your app in the App Centre](.tools/docs/app_manifest.md)
- [Offer your app's functions in napari, Fiji and QuPath](.tools/docs/tools_bridge.md) (experimental)
- [Write notebooks that run in both Colab and JupyterLab](.tools/docs/notebook_portability.md)
- [See what others have built](.tools/docs/use_cases.md)
- [All guides](.tools/docs/README.md)

## Contributing and questions

Bug fixes and improvements are welcome: read the [contributing guidelines](.github/CONTRIBUTING.md). Using LabConstrictor, or stuck? [Open an issue](https://github.com/CellMigrationLab/LabConstrictor/issues).

## Citation

If you use LabConstrictor in your research, please cite the project to support its development:

Iván Hidalgo-Cenalmor, Marcela Xiomara Rivera Pineda, Bruno M. Saraiva, Ricardo Henriques, and Guillaume Jacquemet. **Packaging Jupyter notebooks as installable desktop apps using LabConstrictor. arXiv preprint 2026** DOI: https://doi.org/10.48550/arXiv.2603.10704
