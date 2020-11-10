// start updating the status as soon as the page loads
setTimeout(function() {
  studyId = document.querySelector("#status").attributes["studyid"].value;
  updateDownloadStatus(studyId);
})

function updateDownloadStatus() {

  // call the flask api to trigger/update the status
  fetch("/api/studies/" + studyId + "/archive")
    .then(response => {return response.json()})
    .then(download => {
      document.querySelector("#status").innerHTML = download["status"];

      if (download["status"].startsWith("ready")) {
        console.log("download is ready");
        downloadStudy(download)
      } else {
        console.log(download);
        setTimeout(updateDownloadStatus, 2000);
      }
    })
    .catch(error => {
      console.error(error);
      setTimeout(updateDownloadStatus, 2000);
    })

}

// triggers the download by opening the archive page in the browser
function downloadStudy(download) {
  downloadUrl = download["download-url"]
  console.log("will now trigger download of " + downloadUrl);
  window.location = downloadUrl;
}