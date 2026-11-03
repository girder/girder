# Girder Test Container

A dedicated test container for running Girder's test suite. (Not to be confused with the project's root level `Dockerfile` and `docker-compose.yml`, which are for development).


## How to Use

Have at least Docker v25.0 and Docker Compose v2.20.2 installed.

  1. Create an `.env` file with your UID and GID: `echo -e "UID=$(id -u)\nGID=$(id -g)" > .env`
  2. Build the container: `docker compose build`
  3. Run all tests: `docker compose run --rm runner`

Note the last command is `run`, not `up` as there's no need for the containers to persist once all tests complete.

You can specify a subset of tests by passing in `-e [comma-separated test names]` to the end of the run command, such as `docker compose run --rm runner -e lint,pytest`.

To get an interactive shell, run `docker compose run --rm --entrypoint bash runner`


## What's Up With UID and GID?

As Docker does not run `chown` on bind-mounted volumes, by specifying the current user's UID and GID the container gets user read and write permissions without having to involve `sudo` or a root user.
