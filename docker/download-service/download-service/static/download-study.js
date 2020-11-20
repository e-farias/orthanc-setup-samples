// start updating the status as soon as the page loads
setTimeout(function() {
  studyId = document.querySelector("#status").attributes["studyid"].value;
  sessionId = getRandomSessionId();

  updateDownloadStatus(studyId, sessionId);
})

function getRandomSessionId() {
  id = "";
  for (i=0; i < 20; i++) {
    id += Math.floor(Math.random() * 16).toString(16);
  }
  return id;
}

function updateDownloadStatus(studyId, sessionId) {

  // call the flask api to trigger/update the status
  fetch("/api/studies/" + studyId + "/archive?sessionId=" + sessionId)
    .then(response => {return response.json()})
    .then(download => {
      if (download["status"] == "CreatingArchive") {
        document.querySelector("#status").innerHTML = download["status"] + " " + download["archiveCreationProgress"] + "%";
      } else {
        document.querySelector("#status").innerHTML = download["status"];
      }

      if (download["status"].startsWith("ReadyForDownload")) {
        console.log("download is ready");
        downloadStudy(download)
      } else {
        console.log(download);
        setTimeout(() => {updateDownloadStatus(studyId, sessionId);}, 2000);
      }
    })
    .catch(error => {
      console.error(error);
      setTimeout(() => {updateDownloadStatus(studyId, sessionId);}, 2000);
    })

}

// triggers the download by opening the archive page in the browser
function downloadStudy(download) {
  downloadUrl = download["downloadUrl"]
  console.log("will now trigger download of " + downloadUrl);
  window.location = downloadUrl;
}