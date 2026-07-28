# Girder Test Container

A dedicated test container for running Girder's test suite. (Not to be confused with the project's root level `Dockerfile` and `docker-compose.yml`, which are for development).


## How to Use

Make sure you have at least Docker v25.0 and Docker Compose v2.20.2 installed. You will also need the `/dev/fuse/` device node available for FUSE tests.

  1. Create an `.env` file with your UID and GID: `echo -e "UID=$(id -u)\nGID=$(id -g)" > .env`
  2. Build the container (any time the UID and GID changes) `docker compose build`
  3. Run all tests: `docker compose run --rm runner`

Note the last command is `docker compose run`, not `docker compose up` as there's no need for the containers to persist once all tests finish.

You can specify which subset of tests to run by passing in `-e [comma-separated test names]` to the end of the run command, such as `docker compose run --rm runner -e lint,pytest`.

To clear everything after testing, run `docker compose down --volumes --remove-orphans`.

To get an interactive shell, run `docker compose run --rm --entrypoint bash runner`


## What's Up With UID and GID?

As Docker does not run `chown` on bind-mounted volumes, specifying the current user's UID and GID give the container's user read and write permission without having to involve a root user.
