# JupyterLab Guide

LabConstrictor uses JupyterLab as the interface to run Jupyter notebooks. Using a welcome notebook to guide users, LabConstrictor provides a user-friendly way to access and run notebooks without needing much technical knowledge about JupyterLab. Still, we think that it is good to familiarise yourself with it. So, in case you are not familiar with JupyterLab, this guide is for you!

If you are here just to fix issues with JupyterLab, please go to the [last section of this guide](#fixing-jupyterlab-issues).

## How is a regular JupyterLab session like?

### 1. Launching JupyterLab

When you launch JupyterLab, in the terminal you will see some log messages and a URL (this is important, please check [terminal guide](jupyterlab_terminal.md)), and a new tab will open in your default web browser. The welcome page (or Launcher) looks like this:

![JupyterLab Launcher](https://github.com/CellMigrationLab/LabChronicle/blob/doc_source/JupyterLab_Launcher.png)

### 2. Launching a notebook

In our case, we are mostly interested in running notebooks. For that you have three options:
 - Click on the "Python 3" button under the "Notebook" section, the orange box in the image above ⬆️. This will create a new notebook from scratch and open it in a new tab.
 - Go to the file explorer (red box in the image above ⬆️), navigate to the folder where your notebook is located, and double click on the notebook file (with .ipynb extension, like the blue cursor bellow ⬇️). This will open the notebook in a new tab.
 - In case you are not able to find the notebook in your file explorer, you can always upload it by clicking on the upload button (green box in the image bellow ⬇️). This will open a file dialog where you can select the notebook file from your computer. Once uploaded, you can double click on it to open it in a new tab (like the blue cursor bellow ⬇️).

![Upload button](https://github.com/CellMigrationLab/LabChronicle/blob/doc_source/Open_Notebook.png)

### 3. Notebook interface

Once you have opened a notebook, you will see something like this:

![JupyterLab Notebook Interface](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/JupyterLab_Notebook.png)

If you want to know more about interacting with notebooks, please continue to next section.

## Interacting with notebooks

When interaction with notebooks there are two sections that are important to understand: the toolbar and the notebook cells.

### Toolbar

![Notebook Toolbar](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/JupyterLab_Notebook_Toolbar.png)

1. Save: This button save the current state of your notebook. Important to save your work frequently to avoid losing any changes.
2. Add Cell: This button adds a new cell bellow the selected cell (by defaults it is a code cell, but you can change it with option 10).
3. Cut Cell: This button cuts the selected cell and copies it to the clipboard. You can paste it later with option 5.
4. Copy Cell: This button copies the selected cell to the clipboard. You can paste it later with option 5.
5. Paste Cell: This button pastes the cell from the clipboard bellow the selected cell.
6. Run Cell: This button runs the selected cell and moves to the next cell (you get the same effecy by running the shortcut `Shift + Enter`). If you want to run the cell and stay on it, you can use the keyboard shortcut `Ctrl + Enter`.
7. Interrupt Kernel: This button stops the process that is currently running (e.g. if a cell is taking too long to execute or you are not getting the expected output).
8. Restart Kernel: This button restarts your notebook session, it will clean all the values in memory and stop any process that is currently running. This is useful when you want to start fresh or if you are getting errors that you cannot solve.
9. Restart Kernel and Run All Cells: This button restarts your notebook session (like option 8) and runs all the cells in the notebook from top to bottom. 
10. Cell Type: This dropdown menu allows you to change the type of the selected cell. The most common types are "Code" (for writing and running code) and "Markdown" (for writing formatted text).

### Notebook cells

This options will only appear when you choose one of the cells in the notebook.

![Notebook Cell](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/JupyterLab_Notebook_Cell.png)

1. Create a duplicate of the cell bellow the selected cell.
2. Moves the actual cell up (in the image above ⬆️, it would move the Step 2 on top of Step 1).
3. Moves the actual cell down (in the image above ⬆️, it would move the Step 2 bellow Step 3).
4. Insert a new cell above the selected cell (in the image above ⬆️, it would insert a new cell between Step 1 and Step 2). 
5. Insert a new cell bellow the selected cell (in the image above ⬆️, it would insert a new cell between Step 2 and Step 3).
6. Delete the selected cell.
7. Collapse the cell's content. This is useful when you have a long cell and you want to hide its content to make it easier to navigate through the notebook. Still, when clicking on the collapsed cell, it will expand it again.
8. Execution number, indicates the order in which the cells were executed during the current session. When you run a cell, it will be assigned a number that indicates its execution order (e.g. [1], [2], etc.). If a cell has an asterisk instead of a number (e.g. [*]), it means that the cell is currently running and has not finished yet.
9. Output area, this is where the output of the cell will be displayed after running it. The output can be text, images, tables, etc., depending on the code that you have in the cell.

## Fixing JupyterLab issues

### JupyterLab is not opening in my browser

Please check the [terminal guide](jupyterlab_terminal.md) to see where you can find the URL to access JupyterLab. You can copy and paste this URL into your browser to access JupyterLab.

### I have closed the JupyterLab tab in my browser, how can I open it again?

Please check the [terminal guide](jupyterlab_terminal.md) to see where you can find the URL to access JupyterLab. You can copy and paste this URL into your browser to access JupyterLab.

### I get "Kernel has died" error when running a cell

This error can be caused by different reasons, but the most common one is that the cell is trying to use more resources than your computer can handle. Restart your kernel with `Option 8` on the [toolbar section](#toolbar), then you will need to run the cells again to get back to the same state as before. If you are still getting the error, try reducing resources (e.g. by reducing the number of iterations in a loop) or contact the authors of the notebook.