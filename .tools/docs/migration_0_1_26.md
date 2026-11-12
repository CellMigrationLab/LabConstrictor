# Template 0.1.26: the app's own documentation explains PyPI publishing

Design note for the 0.1.26 migration (`.template_sync/migrations/v0_1_25_to_v0_1_26.py`). It changes documentation only.

## 1. The problem

Template 0.1.25 ([migration_0_1_25.md](migration_0_1_25.md)) added opt-in PyPI publishing to every app: `publish_pypi.yml` and `pypi_package.py`. Its migration did not touch the app's documentation, so an app's own `.tools/docs/external_code_upload.md` still ended at "3. How to import into your notebook", and its `troubleshooting.md` had no PyPI entry. The one-time setup (a pending publisher on pypi.org, the repository variable `PYPI_PUBLISH`) was described only in the template's documentation. The Playground's synchronisation pull request to 0.1.25 showed it.

## 2. What the migration does

Each step is independent, idempotent, never deletes and never raises for a customised file, and keeps the line endings of each file. Both texts are the template's, byte for byte, frozen in `.template_sync/resources/v0_1_25_to_v0_1_26/.tools/docs/`.

* **`.tools/docs/external_code_upload.md`** gets the section **4. Publish the code on PyPI (optional)**. A page that already has the section is unchanged. A page with a section 4 of its own is left as it is (`SKIPPED`).
* **`.tools/docs/troubleshooting.md`** gets the entry **Publishing to PyPI fails**, unless it already has it. The apps' troubleshooting pages differ from the template's (they have entries of their own), so the end of the content is the only place that fits all of them.
* **Where the text goes:** at the end of the page's content, just before the Previous / Home / Next links (a `---` line, then `<div align="center">` ... `</div>`). The links stay the last thing on the page: if text followed them, the migration moves them to the bottom. A page without these links gets the text at its end.
* A missing page is not created.

The template's own `troubleshooting.md` had its links in the middle of the page: the entries of 0.1.23, 0.1.24 and 0.1.25 were added after them. In 0.1.26 they are at the bottom, and a test checks that every documentation page of the template ends with its links. The apps' troubleshooting pages were not affected: no migration added those entries to them.

Why not more:

* **The pages are not replaced.** The apps' copies differ from the template's (the title "Adding External Code", other Previous / Next links, entries of their own), so only the new section is added.
* **The docs index (`.tools/docs/README.md`) is not changed.** Its entry for the page differs from app to app (`#### 3. [*(Optional)* **Upload external code**](./external_code_upload.md)`, `- [Upload external code (optional)](external_code_upload.md)`, ...) and still leads to the page.

## 3. The texts work in an app

* **No placeholder.** The form does not fill in an app's documentation, so the "Name" row of the section no longer shows `PYTHON_PROJ_NAME`: it says the name is the `name=` of `setup.py`.
* **Links.** The relative links lead to pages every app has (`external_code_upload.md`, `troubleshooting.md`, `executable_creation.md`). The design note of 0.1.25, which apps do not have, is linked by its address on GitHub, in the template's pages too.

## 4. What is checked here, and what is not

* Tests (`tests/test_template_sync_0_1_26.py`): the frozen texts turn the template's pages of 0.1.24 into the live pages (the troubleshooting page with its links in the middle, which end at the bottom); every documentation page of the template ends with its links; the texts have no placeholder and no link to a page apps lack; an app's page (another title, other links, CRLF) gets the section before its links and keeps CRLF; a troubleshooting page with links, with text after its links, without links; a page with its own section 4, pages that already explain it, missing and unreadable pages; a second run changes nothing; the sync chain from 0.1.25.
* The migration was also run on copies of real apps (see the pull request).
