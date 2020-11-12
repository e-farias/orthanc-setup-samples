# Purpose

This is a sample setup to demonstrate how to implement a download page
in Orthanc that will:

- create an archive job asynchronously
- monitor the job and display the progress to the user
- trigger the download once it is ready
- make downloads resumable in case a network failure occurs during the download

# Starting the setup

To start the setup, type: `docker-compose up --build`

# demo

- Orthanc is accessible at [http://localhost:8042](http://localhost:8042)
- upload a study
- open the Osimis WebViewer and click the download button
- the download page will open
- by playing with the Chrome dev-tools, you can modify your network conditions, simulate a network connection breakdown while the file is downloading, restore the network and resume the download.

# how it works

Orthanc is started with python plugins that overrides the `/study/{id}/archive` route:

- the GET requests are redirected to a page served by a Flask server (the download service).
- the POST requests (to create asynchronous archive jobs) are redirected to the original Orthanc API

A Flask server provides:

- a `/api/studies/{id}/archive` route that is in charge of triggering the download if it is not started yet and provide the status of the job if a job is already running for this study
- a "download page" that creates the job and shows its status (queued - preparing download (XX %) - ready for download)
- the flask server downloads the file from orthanc to store it in a temporary storage such that nginx will be able to serve it
- the download page triggers the download in the browser once it is ready

An nginx server is used to serve the zip files and provides the "Accept-Ranges" HTTP header (note: flask can probably do it as well but it's not immediate)


Point of attention:

- `"MediaArchiveSize"` defines the number of archives that are kept active -> it is set to 10 in this demo
- `"JobsHistorySize"` defines the number of jobs in the history (they are used to retrieve the archive url) -> it is set to 100 in this demo


# TODO

- Right now, when clicking the download button in the OsimisViewer, the "download page" opens in the same browser tab -> we should provide an option in the viewer
to open this link in a new window
- make the download page look good !
- handle errors in the download page !
- cleanup the `downloadJobs` map in the flask server
- move the flask server inside the python plugin to have a self-contained solution (that probably requires a few extra hours of work)




