# Purpose

This is a sample setup to demonstrate the usage of the Orthanc basic-authentication.

# Description

This demo contains:

- 3 Orthanc containers in which we have configured the basic authentication 3 different ways.

# Starting the setup

To start the setup, type: `docker-compose up --build`

# demo

## Orthanc 1: no authentication

- Open this url in your browser:[http://localhost:8042](http://localhost:8042); no authentication is required  

## Orthanc 2: custom users

- Open this url in your browser:[http://localhost:8043](http://localhost:8043); login with 'me' and 'mypassword'.  These login/pwd have been defined in the docker-compose.

## Orthanc 3: default password

- Open this url in your browser:[http://localhost:8044](http://localhost:8044); login with 'orthanc' and a password that you'll find in the logs.  In this setup, no login/pwd
have been defined in the docker-compose so the container has generated one when starting.  Note that this password will change every time the container is restarted.  


