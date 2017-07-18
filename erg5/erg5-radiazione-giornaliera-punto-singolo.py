# encoding: utf-8

"""Esempio di utilizzo dei dati ERG5.

Questo script permette di scaricare il pacco dati del giorno dal dataset ERG5,
estrarre la radiazione giornaliera e scaricare poi un singolo punto dalla
griglia. Il punto di griglia viene stampato su stdout sotto forma di CSV
"lat,lon,value,distance" (il dato mancante è una stringa vuota).

E' necessario creare (o selezionare) un progetto nella Google Developers
Console e scaricare il file client_secret.json. Si veda il tutorial
https://developers.google.com/drive/v3/web/quickstart/python per maggiori
informazioni.

Per la parte di lettura del file scaricato, viene usata la libreria gribapi.

Author: Emanuele Di Giacomo <edigiacomo@arpae.it>
License: GPLv3

Copyright (C) 2017 Arpae-SIMC
"""

import argparse

import httplib2
import apiclient
import oauth2client

import gribapi


# User agent dell'applicazione
APPLICATION_NAME = "erg5-radiazione-giornaliera-punto-singolo"
# Permessi dell'applicazione: ci basta poter leggere i dati e i metadati dei
# file su Drive.
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
]
# Id del folder di ERG5
# https://drive.google.com/drive/folders/0B7KLnPu6vjdPVGJKR3E4SEluU0U
ERG5_FOLDER_ID = "0B7KLnPu6vjdPVGJKR3E4SEluU0U"


def get_credentials(clientsecret_path, credential_path, args):
    """Restituisce le credenziali per l'applicazione da file.

    Se il file delle credenziali non è presente oppure le credenziali non sono
    valide, allora ne vengono richieste di nuove.

    Args:
        clientsecret_path: file client_secret.json ottenuto dalla Google
            Developers Console
        credential_path: path del file in cui salvare le credenziali
        args: argomenti da linea di comando.

    Returns:
        Le credenziali ottenute
    """
    # Inizializzo lo storage per le credenziali e provo a leggerle
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    # Se non esiste il file oppure le credenziali non sono valide, le creo
    if not credentials or credentials.invalid:
        flow = oauth2client.client.flow_from_clientsecrets(clientsecret_path,
                                                           SCOPES)
        flow.useragent = APPLICATION_NAME
        credentials = oauth2client.tools.run_flow(flow, store, args)

    return credentials


def write_erg5_file(fp, httpclient, refdate):
    """Scrive il file ERG5 del giorno richiesto.

    Args:
        fp: file object in cui viene scritto il file.
        httpclient: client per API Google
        refdate: oggetto datetime.date che indica il giorno richiesto
    """

    # Query per https://developers.google.com/drive/v3/reference/files/list
    # Il nome è quello del file relativo al giorno richiesto e deve essere
    # contenuto nel folder ERG5
    query = (
        "name = 'erg5.{refdate:%Y%m%d}0000.grib' "
        "and "
        "'{folder}' in parents"
    ).format(refdate=refdate, folder=ERG5_FOLDER_ID)
    service = apiclient.discovery.build('drive', 'v3', http=httpclient)
    files = service.files().list(q=query).execute().get("files", [])
    # Se il file esiste, lo scrivo nel fp
    if len(files):
        request = service.files().get_media(fileId=files[0]["id"])
        media_request = apiclient.http.MediaIoBaseDownload(fp, request)
        while True:
            download_progress, is_done = media_request.next_chunk()
            if is_done:
                break


def get_grib_radiation_daily(filename):
    """Restituisce il gribid all'interno del file che contiene la radiazione
    giornaliera.

    Args:
        filename: nome del file GRIB

    Returns:
        Il gribid del messaggio contenente la radiazione giornaliera oppure
        None se il messaggio non è presente.
    """

    # Funzione inline che restituisce il valore del metadato dal GRIB oppure
    # None se non lo trova (gribapi.grib_get lancerebbe un'eccezione)
    grib_get_or_none = lambda gid, key: gribapi.grib_get(gid, key) if gribapi.grib_is_defined(gid, key) else None

    with open(filename) as fp:
        # Itero sui messaggi GRIB
        while True:
            gid = gribapi.grib_new_from_file(fp)
            # Quando è None, non ho più messaggi
            if gid is None:
                return None
            # Il messaggio GRIB desiderato deve avere i seguenti metadati
            if all([
                # Categoria: Short-wave Radiation
                grib_get_or_none(gid, "parameterCategory") == 4,
                # Prodotto: Downward short-wave radiation flux (W m-2)
                grib_get_or_none(gid, "parameterNumber") == 7,
                # Processing: Accumulation
                grib_get_or_none(gid, "typeOfStatisticalProcessing") == 1,
                # Generating process: Observation
                grib_get_or_none(gid, "typeOfGeneratingProcess") == 8,
                # Time Unit: Hour
                grib_get_or_none(gid, "indicatorOfUnitOfTimeRange") == 1,
                # Time range: 24
                grib_get_or_none(gid, "lengthOfTimeRange") == 24
            ]):
                # Se è lui, lo restituisco
                return gid

    return None


def parse_datestring(datestr):
    """Semplice parser per le date nella forma YYYY-mm-dd"""
    from datetime import datetime
    return datetime.strptime(datestr, "%Y-%m-%d")


if __name__ == '__main__':
    # Inizializzo il parser da linea di comando con le opzioni per le
    # credenziali OAuth2 di Google. Si veda
    # https://oauth2client.readthedocs.io/en/latest/source/oauth2client.tools.html#oauth2client.tools.run_flow
    # per maggiori informazioni sulle opzioni disponibili.
    parser = argparse.ArgumentParser(parents=[oauth2client.tools.argparser])
    parser.add_argument("client_secret", help="File client_secret scaricato da Google Developers Console")
    parser.add_argument("credential", help="File in cui salvare le credenziali")
    parser.add_argument("refdate", type=parse_datestring, help="Data di riferimento (e.g. 2017-01-01)")
    parser.add_argument("longitude", type=float, help="Longitudine del punto")
    parser.add_argument("latitude", type=float, help="Latitudine del punto")

    args = parser.parse_args()

    credentials = get_credentials(args.client_secret, args.credential, args)
    httpclient = credentials.authorize(httplib2.Http())

    # Salvo il pacco dati GRIB in un file locale
    gribfilename = "erg5.{refdate:%Y%m%d}0000.grib".format(refdate=args.refdate)
    with open(gribfilename, "wb") as fp:
        # Scrivo il pacco dati
        write_erg5_file(fp, httpclient, args.refdate)

    # Dal pacco dati appena scritto, estraggo la radiazione giornaliera
    with open(gribfilename, "rb") as fp:
        gid = get_grib_radiation_daily(fp.name)
        # Se è None, vuol dire che non l'ho trovata
        if gid is None:
            raise Exception("Radiazione giornaliera non trovata")
        else:
            # Prendo il valore del missing value
            missing = gribapi.grib_get(gid, "missingValue")
            # Estraggo il punto più vicino (può lanciare un'eccezione se il
            # punto è fuori dalla griglia).
            point = gribapi.grib_find_nearest(gid,
                                              args.latitude,
                                              args.longitude,
                                              is_lsm=False,
                                              npoints=1)
            # Se il valore è un missing, lo sostituisco con una stringa vuota
            if point[0]["value"] == missing:
                point[0]["value"] = ""
            # Stampo il CSV con il risultato
            print("{lat},{lon},{value},{distance}".format(**point[0]))
