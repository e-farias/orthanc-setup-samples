import io
import orthanc
import pprint
import inspect
import numbers


def OnRestStudyArchive(output, uri, **request):
    # Retrieve the study ID from the regular expression (*)
    studyId = request['groups'][0]

    if request['method'] == 'GET':

        # open a specific HTML page that is served by the flask server, that will monitor the creation
        # of the archive and trigger the download once it is ready
        output.Redirect(f"http://localhost:5000/studies/{studyId}/archive")

    else:

        pprint.pprint(request)
        # forward the POST request to the original Orthanc API
        output.AnswerBuffer(orthanc.RestApiPost(f"/studies/{studyId}/archive", request["body"]), "application/json")


# overrides the Orthanc archive route
orthanc.RegisterRestCallback('/studies/(.*)/archive', OnRestStudyArchive)  # (*)
