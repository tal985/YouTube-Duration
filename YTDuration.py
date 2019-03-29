# Sample Python code for user authorization

import os
import isodate
import datetime
import sys

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from oauth2client import client
from oauth2client import tools 
from oauth2client.file import Storage 

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

def get_authenticated_service():

    store = Storage("credential_sample.json")
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS_FILE, SCOPES)
        credentials = tools.run_flow(flow, store)

    return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)

# Find the channel ID from a username
def get_id_from_username(service, **kwargs):

    results = service.channels().list(**kwargs).execute()

    if results["items"]:
        return results["items"][0]["id"]
    return None

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):

    good_kwargs = {}
    if kwargs is not None:
        for key, value in kwargs.items():
            if value:
                good_kwargs[key] = value
    return good_kwargs

def search_list_by_keyword(client, **kwargs):

    kwargs = remove_empty_kwargs(**kwargs)
    try:
        response = client.search().list(**kwargs).execute()
    except Exception as e:
        print (e)
        return None

    return response

# Find the duration of the video from the video ID
def get_duration_from_vid(client, **kwargs):

  kwargs = remove_empty_kwargs(**kwargs)
  response = client.videos().list(**kwargs).execute()
  return response["items"][0]["contentDetails"]["duration"]

# Sum up all the duration of the videos on the current "page" 
def process_response_page(response):

    global totalDur
 
    if "items" in response and response["items"]:
        vidlist = response["items"] 
    else:
        sys.exit("No results found.")

    for item in vidlist:
        tempDur = get_duration_from_vid(service, 
            part = "contentDetails", 
            fields = "items/contentDetails/duration", 
            id = item["id"]["videoId"])
        tempDur = isodate.parse_duration(tempDur)
        totalDur += tempDur
        print("Video Duration: " + str(tempDur))

    print("Total Duration (So Far): " + str(totalDur))

if __name__ == "__main__":

    if len(sys.argv) != 3:
        sys.exit("Invalid amount of arguments.")
    url = sys.argv[1]
    searchterm = 'intitle:"' + sys.argv[2] + '"'
    sys.argv = [sys.argv[0]]
    totalDur = datetime.timedelta()
        
    # When running locally, disable OAuthlib's HTTPs verification. When
    # running in production *do not* leave this option enabled.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    service = get_authenticated_service()

    #URL will turn to a user name or channel ID
    #Legacy username format
    if "www.youtube.com/user/" in url:
        index = url.index("r/")
        url = url[index + 2:]
        if "/" in url:
            index = url.index("/")
            url = url[:index]
        id = get_id_from_username(service, 
            part = "snippet",
            fields = "items/id",
            forUsername = url)
    #New channel format
    elif "www.youtube.com/channel/" in url:
        index = url.index("l/")
        url = url[index + 2:]
        if "/" in url:
            index = url.index("/")
            url = url[:index]
        id = url
    else:
        sys.exit("Malformed URL.")

    if id:
        #Get first page
        temp = search_list_by_keyword(service, 
            part = "id",
            channelId = id,
            fields = "nextPageToken, items/id/videoId",
            maxResults = 50,
            q = searchterm,
            type = "video")

        #If first page exists
        if temp:
            process_response_page(temp)

            #if there's a next page
            if "nextPageToken" in temp:
                nextpage = temp["nextPageToken"]
            else:
                nextpage = None

            #While there's a next page
            while nextpage:
                #Get the next page as the current page
                temp = search_list_by_keyword(service, 
                    part = "snippet",
                    channelId = id,
                    fields = "nextPageToken, items/id/videoId",
                    maxResults = 50,
                    q = searchterm,
                    type = "video",
                    pageToken = nextpage)

                #If the current page exists, process then update the next page token
                if temp:
                    process_response_page(temp)
                    if "nextPageToken" in temp:
                        nextpage = temp["nextPageToken"]
                    else:
                        nextpage = None