from flask import Flask, jsonify, send_from_directory, render_template, request, Response, abort
import json
import dataclasses
import requests
import os
import pprint
import datetime
import threading
import time
import glob
import multiprocessing
from enum import Enum

############## APP configuration through env var

staticFolder = os.path.join(os.path.dirname(__file__), "static")
archivesFolder = os.environ.get("ARCHIVES_FOLDER", os.path.join(os.path.dirname(__file__), "archives"))
orthancInternalUrl = os.environ.get("ORTHANC_INTERNAL_URL", "http://localhost:8044")
downloadPublicUrl = os.environ.get("DOWNLOAD_PUBLIC_URL", "http://localhost:80")
expirationAfterMinutes = (float)(os.environ.get("EXPIRATION_AFTER_MINUTES", "60"))

def getArchivePath(downloadId: str):
  return os.path.join(archivesFolder, f"{downloadId}.zip")

############## Flask server initialization

app = Flask(__name__, template_folder=staticFolder)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

class DownloadServiceJsonEncoder(json.JSONEncoder):
  def default(self, o):
    if dataclasses.is_dataclass(o):
      return dataclasses.asdict(o)
    elif isinstance(o, DownloadStatus):
      return o.name
    elif isinstance(o, datetime.datetime):
      return str(o)
    return super().default(o)

app.json_encoder = DownloadServiceJsonEncoder


#########################################################

downloads = {}
archivesToCopy = multiprocessing.Queue()

class DownloadStatus(Enum):
  Queued = 1                    # while the orthanc job is in the job queue
  CreatingArchive = 2           # while the orthanc job is processing
  CopyingArchive = 3            # while we're copying the archive from Orthanc to server storage
  ReadyForDownload = 4          # once ready for download from nginx


@dataclasses.dataclass
class Download:

  studyId: str
  sessionId: str
  jobId: str = None
  archiveCreationProgress: float = 0
  downloadUrl: str = None
  status: DownloadStatus = DownloadStatus.Queued
  createdAt: datetime.datetime = datetime.datetime.now()
  lastAccessedAt: datetime.datetime = datetime.datetime.now()

def touch(downloads, downloadId):
  download = downloads[downloadId]
  download.lastAccessedAt = datetime.datetime.now()
  downloads[downloadId] = download

def downloadArchiveFromOrthanc(downloadId: str, downloads):
  print(f"downloading file from orthanc for {downloadId}")

  download = downloads[downloadId]
  archive = requests.get(f"{orthancInternalUrl}/jobs/{download.jobId}/archive").content

  with open(getArchivePath(downloadId), "wb") as f:
    f.write(archive)

  download.downloadUrl = f"{downloadPublicUrl}/{downloadId}.zip"
  download.status = DownloadStatus.ReadyForDownload
  downloads[downloadId] = download
  print(f"downloading file from orthanc for {downloadId}: completed")

def copyArchiveWorkerFunction(archivesToCopy, downloads):
  print("starting the copy archive worker")
  while True:
    try:
      downloadId = archivesToCopy.get()
      if downloadId is None: # this is the "exit" signal
        return

      downloadArchiveFromOrthanc(downloadId, downloads)
    except Exception as e:
      print(f"error while copying archive from Orthanc to WebServer: {str(e)}")
    except KeyboardInterrupt as e:
      print(f"exiting ...")  

def cleanupWorkerFunction(downloads, shouldStop):
  print("starting the cleanup worker")

  lastCleanup = datetime.datetime.now()

  while True:
    try:
      time.sleep(1) # short interval to exit quickly when required
      if shouldStop.value:
        return

    except KeyboardInterrupt as e:
      print(f"exiting ...")  

    now = datetime.datetime.now()
    sinceLastCleanup = now - lastCleanup
    if sinceLastCleanup.seconds > 60: # run cleanup task every 60 seconds
      lastCleanup = now
      # print("running cleanup")

      for downloadId, download in downloads.items():
        # print(downloadId)
        # pprint.pprint(download)
        if (now - download.lastAccessedAt).seconds > (expirationAfterMinutes * 60):
          try:
            path = getArchivePath(downloadId)
            print(f"deleting expired file {path}")
            os.remove(path)
          except Exception as e:
            print(f"error while cleaning up archives: {str(e)}")

          # delete from memory anyway
          del downloads[downloadId]


def cleanupAtStartup():
  print(f"cleaning the archive folder at startup: {archivesFolder}")
  for path in glob.glob(os.path.join(archivesFolder, "*.zip")):
    try:
      print(f"deleting file at startup: {path}")
      os.remove(path)
    except Exception as e:
      print(f"error while cleaning up archives at startup: {str(e)}")

############## server routes implementation

# API route to trigger the job and monitor its status
# note: user can provide a sessionId in order to have his own dedicated download
# /api/studies/.../archive?sessionId=123456
@app.route('/api/studies/<studyId>/archive', methods=["GET"])
def apiDownloadStudy(studyId):
    sessionId = request.args.get("sessionId") if "sessionId" in request.args else "default-session"

    print(f"user has requested to download study {studyId} in session {sessionId}")

    downloadId = f"{studyId}--{sessionId}"

    if not downloadId in downloads:
      r = requests.post(f"{orthancInternalUrl}/studies/{studyId}/archive", json = {"Asynchronous": True})
      if r.status_code != 200:
        print(f"Could not start downloading the study")
        abort(r.status_code)
      
      job = r.json()
      # pprint.pprint(job)
      print(f"created a new archive job {job['ID']} for study {studyId}")
      download = Download(studyId=studyId, sessionId=sessionId, jobId=job["ID"])
      downloads[downloadId] = download

      return jsonify(download)

    else:

      touch(downloads, downloadId) # keep track that it has been accessed to avoid deleting it too early

      download = downloads[downloadId]
      jobId = download.jobId
      print(f"found an existing download {jobId} for study {studyId} in session {sessionId}")

      job = requests.get(f"{orthancInternalUrl}/jobs/{jobId}").json()
      # pprint.pprint(job)

      downloadUrl = None
      status = "download queued for preparation"
      if job["State"] == "Success":

        if (download.status == DownloadStatus.Queued) or (download.status == DownloadStatus.CreatingArchive)  :
          print(f"downloading from orthanc such that nginx can serve it")  
          download.status = DownloadStatus.CopyingArchive
          download.archiveCreationProgress = 100
          downloads[downloadId] = download
          
          # download from orthanc in another process
          archivesToCopy.put(downloadId)

        elif download.status == DownloadStatus.CopyingArchive:
          # don't do anything, it's being copied right now
          pass
          
      
      elif job["Progress"] >= 1:
        download.status = DownloadStatus.CreatingArchive
        download.archiveCreationProgress = job["Progress"]
        downloads[downloadId] = download
      
      return jsonify(download)

# HTML page to trigger the download and show its progress
@app.route('/studies/<studyId>/archive', methods=["GET"])
def downloadStudyPage(studyId):
  
  return render_template("download-study.html", studyId=studyId)

# to serve the js code of the HTML page
@app.route('/studies/<studyId>/<path>', methods=["GET"])
def downloadStudyStaticContent(studyId, path):
  return send_from_directory(staticFolder, path)


############## Main

if __name__ == '__main__':

  print(f"orthancInternalUrl = {orthancInternalUrl}")
  print(f"downloadPublicUrl = {downloadPublicUrl}")
  print(f"archivesFolder = {archivesFolder}")
  print(f"expirationAfterMinutes = {expirationAfterMinutes}")

  cleanupAtStartup()

  with multiprocessing.Manager() as sharedMemoryManager:

    downloads = sharedMemoryManager.dict()
    shouldStop = multiprocessing.Value('b', False)
    archivesToCopy = multiprocessing.Queue()
    
    copyArchiveWorker = multiprocessing.Process(target=copyArchiveWorkerFunction, args=(archivesToCopy, downloads))
    copyArchiveWorker.start()

    cleanupWorker = multiprocessing.Process(target=cleanupWorkerFunction, args=(downloads, shouldStop))
    cleanupWorker.start()

    app.run(host="0.0.0.0", port=5000)

    # tell the workers to exit
    print("exiting workers")
    shouldStop.value = True
    archivesToCopy.put(None)

    copyArchiveWorker.join()
    cleanupWorker.join()
