from flask import Flask, jsonify, send_from_directory, render_template, request, Response
import requests
import os
import pprint

staticFolder = os.path.join(os.path.dirname(__file__), "static")
archivesFolder = os.path.join(os.path.dirname(__file__), "archives")

app = Flask(__name__, template_folder=staticFolder)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


orthancInternalUrl = os.environ.get("ORTHANC_INTERNAL_URL", "http://localhost:8044")
downloadPublicUrl = os.environ.get("DOWNLOAD_PUBLIC_URL", "http://localhost:80")

print(f"orthancInternalUrl = {orthancInternalUrl}, downloadPublicUrl = {downloadPublicUrl}")
downloadJobs = {}

# API route to trigger the job and monitor its status

@app.route('/api/studies/<studyId>/archive', methods=["GET"])
def apiDownloadStudy(studyId):
    print(f"user has requested to download study {studyId}")

    if not studyId in downloadJobs:
      job = requests.post(f"{orthancInternalUrl}/studies/{studyId}/archive", json = {"Asynchronous": True}).json()
      pprint.pprint(job)
      print(f"created a new archive job {job['ID']} for study {studyId}")
      downloadJobs[studyId] = job["ID"]
      return jsonify({
        "studyId": studyId,
        "job": job,
        "download-url": None,  # download is not ready yet,
        "status": "download queued for preparation"
      })

    else:

      jobId = downloadJobs[studyId]
      print(f"found an existing job {downloadJobs[studyId]} for study {studyId}")

      job = requests.get(f"{orthancInternalUrl}/jobs/{jobId}").json()
      pprint.pprint(job)

      downloadUrl = None
      status = "download queued for preparation"
      if job["State"] == "Success":
        status = "ready - download will start very soon"
        print(f"downloading from orthanc such that nginx can serve it (TODO: make this asynchronous)")
        archive = requests.get(f"{orthancInternalUrl}/jobs/{jobId}/archive").content

        with open(f"/www/data/{studyId}.zip", "wb") as f:
          f.write(archive)

        downloadUrl = f"{downloadPublicUrl}/{studyId}.zip"
      elif job["Progress"] >= 1:
        status = f"preparing download - {job['Progress']} %"

      return jsonify({
        "studyId": studyId,
        "job": job,
        "download-url": downloadUrl,
        "status": status
      })

# HTML page to trigger the download and show its progress

@app.route('/studies/<studyId>/archive', methods=["GET"])
def downloadStudyPage(studyId):
  
  return render_template("download-study.html", studyId=studyId)

# to serve the js code of the HTML page
@app.route('/studies/<studyId>/<path>', methods=["GET"])
def downloadStudyStaticContent(studyId, path):
  return send_from_directory(staticFolder, path)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)