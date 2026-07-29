# Data Model

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

# DEPRECATED
This was genuinely the repo that set us on our current path. The importance of what is here cannot be understated. And yet the march of progress never slows. Management of the data model now resides in the monorepo.

<details>
<Summary>Original ReadMe</Summary>
    
# Overview

This repository defines the F3 data structure, used by the F3 Slack Bot, Maps, etc. The projected uses SQLAlchemy to define the tables / models.

# Running Locally

To load the data structure in your database:

1. Set up a local db, update `.env.example` and save as `.env`
2. Clone the repo, use Poetry to install dependencies:

```sh
poetry env use 3.12
poetry install
```

3. Run the alembic migration:

```sh
source .env && poetry run alembic upgrade head
```

# Optional BigQuery Sessions

The default database session path is PostgreSQL. To explicitly request a BigQuery session, pass the optional `backend` argument:

```python
from f3_data_models.utils import get_session

postgres_session = get_session()
bigquery_session = get_session(backend="bigquery")
```

`session_scope(...)` and `DbManager` methods also accept the same optional `backend` argument.

BigQuery mode requires these environment variables:

- `BIGQUERY_PROJECT`
- `BIGQUERY_DATASET`

Authentication should be provided through Google Application Default Credentials in the runtime environment.

# Contributing

If you would like to make a change, you will need to:

1. Make the change in `models.py`
2. Make a alembic revision:

```sh
source .env && alembic revision --autogenerate -m "Your Message Here"
```

3. Make any edits to the migration script in `alembic/versions`
4. Run the upgrade on your local db:

```sh
source .env && alembic upgrade head
```

5. Bump the version on `pyproject.toml`:

```sh
poetry version patch[minor][major]
```

6. Tag your final commit and make sure to push those tags to trigger the pypi package build:

```sh
git tag <new_version> -a -m "Your message here"
git push origin --tags
```

> [!NOTE]
> The github pages documentation will be updated when you push to `main`, but if you would like to preview locally, run:

```sh
poetry run sphinx-build -b html docs docs/_build/html
cd docs
poetry run python -m http.server --directory _build/html
```

> [!TIP]  
> Adding new fields as nullable (ie `Optional[]`) has the best chance of reducing breaking changes to the apps.

# Entity Overview

```mermaid
---
config:
    look: handDrawn
    theme: dark
---

erDiagram
    USERS ||--|{ ATTENDANCE : have
    ATTENDANCE }|--|| EVENT_INSTANCES: at
    ATTENDANCE }|..|{ ATTENDANCE_TYPES : "are of type(s)"
    EVENT_INSTANCES }|..|| EVENTS : "part of series"
    EVENT_INSTANCES }|..|{ EVENT_TYPES : "with type(s)"
    EVENTS }|..|{ EVENT_TYPES : "with type(s)"
    EVENT_INSTANCES }|--|| ORGS : "belong to"
    EVENT_INSTANCES }|..|| LOCATIONS : "at"
    EVENTS }|--|| ORGS : "belong to"
    EVENTS }|..|| LOCATIONS : "at"
    SLACK_SPACES ||..|| ORGS : "are connected to"
    USERS ||..|{ SLACK_USERS : "have one or more"
    SLACK_USERS }|--|| SLACK_SPACES : "belong to"
    USERS }|..|{ ACHIEVEMENTS : "earn"
    USERS }|..|{ ROLES : "have"
    ROLES ||..|{ PERMISSIONS : "have"
    ROLES }|..|{ ORGS : "in"
    USERS }|..|{ POSITIONS : "hold"
    POSITIONS }|..|{ ORGS : "in"
```
</details>
