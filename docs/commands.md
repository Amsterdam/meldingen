# Project CLI Commands

## Introduction
This document provides an overview of the Command Line Interface (CLI) commands available within the project. These commands are designed to facilitate various tasks.

## Available Commands

### Users and Groups

#### 1. "users add"
**Description:** Add a user to the system

**Syntax:**
```bash
$ python main.py users add [OPTIONS] COMMAND [ARGS]...

Options:

--help               Show this message and exit.

Arguments

*    email      TEXT  [default: None] [required]
```

Example:

```bash
$ python main.py users add user@example.com
```

#### 2. "groups add"
**Description:** Add a group to the system

**Syntax:**
```bash
$ python main.py groups add [OPTIONS] COMMAND [ARGS]...

Options:

--help               Show this message and exit.

Arguments

*    name      TEXT  [default: None] [required]   
```

Example:

```bash
$ python main.py groups add test-group
```

#### 3. "users add-to-group"
**Description:** Adds a user to a given group

**Syntax:**
```bash
$ python main.py users add-to-group [OPTIONS] COMMAND [ARGS]...

Options:

--help               Show this message and exit.

Arguments

*    email           TEXT  [default: None] [required]                                                                                                                                 │
*    group_name      TEXT  [default: None] [required]   
```

Example:

```bash
$ python main.py users add-to-group user@example.com test-group
```

### Forms

#### 1. "forms add-primary"
**Description:** Adds the primary form to the system, only one primary form can exist.

**Syntax:**
```bash
$ python main.py forms add-primary [OPTIONS]

Options:

--title        TEXT  The title of the primary form [default: None] [required]
--help               Show this message and exit.
```

Example:

```bash
$ python main.py users add-to-group user@example.com test-group
```