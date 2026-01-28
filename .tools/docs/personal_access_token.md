# Generate a GitHub Personal Access Token

To interact with GitHub repositories from your notebook (e.g., cloning, editing, pushing files), you need a GitHub Personal Access Token (PAT). This token authenticates your API calls and grants the necessary permissions. Here there is a GIF with the steps to generate a token:

![Gif of generating a GitHub token](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/GitHub_Access_Token.gif)

For detailed steps, follow the instructions below based on the level of access you need.

## For Read & Write Access

1. Go to https://github.com/ and sign in.  
2. Click your profile icon (top right) ➔ **Settings**  
3. In the left sidebar, select **Developer settings** ➔ **Personal access tokens** ➔ **Tokens (classic)**  
4. On the top right side (at the same level as `Personal access tokens (classic)`), click on  **Generate new token** ➔ **Generate new token (classic)**  
5. Give your token a descriptive **Name** (e.g., `Notebook RW Token`) and set an **Expiration** if desired  
6. Under **Scopes**, check:  
   - **repo**  
     - **contents**  
       > Grants read & write access to repository contents (needed for cloning, editing, and pushing files)
   - *(Optional: To only work with public repositories, select **public_repo** instead of **repo**)*  
7. Click **Generate token** at the bottom  
8. **Copy** your new token immediately — you won’t see it again!  
9. Paste the token into your notebook’s `GitHub-token` field so API calls authenticate as the chosen owner.  

---

## For Read-Only Access

1. Go to https://github.com/ and sign in.  
2. Click your profile icon (top right) ➔ **Settings**  
3. In the left sidebar, select **Developer settings** ➔ **Personal access tokens** ➔ **Tokens (classic)**  
4. Click **Generate new token (classic)**  
5. For **Resource owner**, select the owner of the repository (your user or organization)  
6. Give your token a descriptive **Name** (e.g., `Notebook Read-Only Token`) and set an **Expiration** if desired  
7. Under **Scopes**, check:  
   - **repo**  
     - **contents**  
       > Grants **read-only** access to repository contents (needed for cloning or viewing files only)  
   - *(Optional: For public repositories, select **public_repo** instead of **repo**)*  
8. Click **Generate token** at the bottom  
9. **Copy** your new token immediately—you won’t see it again!  
10. Paste the token into your notebook’s `GitHub-token` field for authentication.  


---

<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 40px;">
  <a href="workflow_status.md" style="flex: 1; text-align: left;">← Previous</a>
  <a href="README.md" style="flex: 1; text-align: center;">🏠 Home</a>
  <a href="" style="color: gray; pointer-events: none; flex: 1; text-align: right;">Next →</a>
</div>