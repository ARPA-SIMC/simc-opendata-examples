# Esempio adattato da https://developers.google.com/drive/v3/web/quickstart/python.
# Licenza: Apache 2.0

from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from apiclient import http
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage


try:
    import argparse
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    # Aggiungo come parametro da linea di comando il giorno di riferimento
    # e.g. 20161116.
    parser.add_argument("erg5_refday", help="YYYYmmdd")
    flags = parser.parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
]
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def main():
    credentials = get_credentials()
    http_client = credentials.authorize(httplib2.Http())

    # Utilizzo le API v2
    service = discovery.build('drive', 'v2', http=http_client)
    # Elenco dei file della directory Drive di ERG5
    children = service.children().list(
        folderId="0B7KLnPu6vjdPVGJKR3E4SEluU0U",
        q="title = 'erg5.{}0000.grib'".format(flags.erg5_refday),
    ).execute().get("items", [])
    if len(children) == 0:
        print("File non trovato")
    else:
        fileId = children[0]["id"]
        child = service.files().get(
            fileId=fileId
        ).execute()
        request = service.files().get_media(fileId=fileId)
        # Scarico il file nella directory corrente usando il nome originale
        # del file
        with open(child["title"], "wb") as fp:
            media_request = http.MediaIoBaseDownload(fp, request)
            while True:
                download_progress, is_done = media_request.next_chunk()
                if is_done:
                    break

if __name__ == '__main__':
    main()
