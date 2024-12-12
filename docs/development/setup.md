# Local setup
This guide explains how to set up and run the project locally using Docker.

## Prerequisites
Before starting with the setup, make sure the following are installed:

- Git
- Docker

## Cloning the repository
Now let's clone the repository:

```bash
git clone https://github.com/Amsterdam/meldingen.git
```

## Copy the `.env.example` to `.env`
After cloning the repository, navigate to the root directory and copy the 
`.env.example` to `.env.`.

## Building the Docker images
While in the root directory now pull the relevant images and build the services:

```bash
cd meldingen/
docker-compose pull
docker-compose build
```

## Starting the containers
To initiate the containers start them by running the following command:

```bash
docker-compose up -d
```

This will launch the following containers:

- **meldingen**: The Meldingen API.
- **database**: PostgreSQL database for storing application data.
- **keycloak**: Keycloak, an Identity Provider for authentication.
- **azurite**: File storage
- **imgproxy**: Image generation / thumbnails etc.
- **docs**: Documentation service.

Once the containers are running, you can access the Meldingen API at 
[http://localhost:8000](http://localhost:8000/docs). The OpenAPI specifications 
are available at [http://localhost:8000/docs](http://localhost:8000/docs), 
and this documentation can be found at [http://localhost:8001/](http://localhost:8001/).

## Restarting the containers after changes
The best way to restart your containers after changes is:

```bash
docker compose down
cp .env.example .env
docker compose build
docker compose up -d
```

## Authentication and authorization

Docker Compose automatically runs a script to add new users to the database.

### Login
You can test authorization pressing the "authorize" button on [the docs page](http://localhost:8000/docs).

The client ID is: ```meldingen```

Leave the client secret empty.

Afterwards you get forwarded to a keycloak login.

The username is ```user@example.com``` and the password ```password```

### Keycloak

The Docker Compose file includes a Keycloak setup to serve as the Identity 
Provider for Meldingen.

### Admin User

A user named `admin` is provided within the `master` realm. This user is 
configured with the username `admin` and password `admin`.

### Default User (meldingen realm)

A default user named `meldingen_user` is provided within the `meldingen` realm. 
This user is configured with the same email address (user@example.com) as the 
user we created earlier in the documentation. The password is `password`.

### Accessing Keycloak

You can access the Keycloak admin console and manage realms, users, and other 
configurations by navigating to [Keycloak](http://localhost:8002/).

For more information on running Keycloak in Docker read the [official documentation](https://www.keycloak.org/getting-started/getting-started-docker).
