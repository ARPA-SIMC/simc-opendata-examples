# encoding: utf-8

"""Esempio di utilizzo dei dati ERG5.

Questo script permette di scaricare il pacco dati del giorno dal dataset ERG5,
e fare il dump in CSV e GeoJSON dei messaggi GRIB, suddivisi per prodotto.

Le colonne dei file CSV e GeoJSON prodotti sono:

* id:  identificativo della cella GIAS.
* date: data nel formato YYYmmdd
* time: ora nel formato HHMM
* lat: latitudine del centro cella
* lon: longitudine del centro cella
* value: valore (se mancante, stringa vuota nel CSV e null nel GeoJSON)

Il nome del prodotto viene dedotto usando un array associativo, in cui ad ogni
chiave (il nome del prodotto) sono associati i valori di una serie di chiavi nel
GRIB (vedi funzione `get_product_name`).

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
import json
import csv

import httplib2
import apiclient
import oauth2client

import gribapi


# User agent dell'applicazione
APPLICATION_NAME = "erg5-dump-data"
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


def get_product_name(gid):
    """Restituisce il nome del prodotto associato al messaggio GRIB passato come
    parametro. Se non lo trova, restituisce None"""

    # Ci sono solo due "prodotti" definiti.
    products = {
        # Temperatura media giornaliera osservata a 1.8m dal suolo (K)
        "temp_daily_avg": {
            "discipline": 0,
            "parameterCategory": 0,
            "parameterNumber": 0,
            "typeOfFirstFixedSurface": 103,
            "scaleFactorOfFirstFixedSurface": 3,
            "scaledValueOfFirstFixedSurface": 1800,
            "typeOfSecondFixedSurface": 255,
            "forecastTime": 0,
            "indicatorOfUnitOfTimeRange": 1,
            "productDefinitionTemplateNumber": 8,
            "typeOfStatisticalProcessing": 0,
            "indicatorOfUnitForTimeRange": 1,
            "lengthOfTimeRange": 24,
            "typeOfProcessedData": 0,
        },
        # Temperatura massima giornaliera osservata a 1.8m dal suolo (K)
        "temp_daily_max": {
            "discipline": 0,
            "parameterCategory": 0,
            "parameterNumber": 0,
            "typeOfFirstFixedSurface": 103,
            "scaleFactorOfFirstFixedSurface": 3,
            "scaledValueOfFirstFixedSurface": 1800,
            "typeOfSecondFixedSurface": 255,
            "forecastTime": 0,
            "indicatorOfUnitOfTimeRange": 1,
            "productDefinitionTemplateNumber": 8,
            "typeOfStatisticalProcessing": 2,
            "indicatorOfUnitForTimeRange": 1,
            "lengthOfTimeRange": 24,
            "typeOfProcessedData": 0,
        },
        # etc...
    }
    # Funzione che restituisce True se la chiave k esiste ed ha valore v
    grib_match_key_long = lambda gid, k, v: gribapi.grib_get_long(gid, k) == v if gribapi.grib_is_defined(gid, k) else False

    for name, matchers in products.items():
        if all(grib_match_key_long(gid, key, value)
               for key, value in matchers.items()):
            return name

    return None


def coords_to_cellid(gid, lon, lat):
    """
    Converte le coordinate di un punto nella corrispondente cella ERG5.

    Se il punto è fuori dalla griglia, restituisce None.
    """
    lat0 = gribapi.grib_get_double(gid, "latitudeOfFirstGridPointInDegrees")
    lon0 = gribapi.grib_get_double(gid, "longitudeOfFirstGridPointInDegrees")
    ncol = gribapi.grib_get_long(gid, "Ni")
    nrow = gribapi.grib_get_long(gid, "Nj")
    latstep = gribapi.grib_get(gid, "jDirectionIncrementInDegrees")
    lonstep = gribapi.grib_get(gid, "iDirectionIncrementInDegrees")

    col = int((lon - lon0) / lonstep)
    row = int((lat - lat0) / latstep)

    if any([col < 0, col >= ncol, row < 0, row >= nrow]):
        return None

    return nrow * col + nrow - row


def get_items(gid):
    """Legge il GRIB e restituisce un array di dizionari contenenti i campi:
        * id: identificativo della cella GIAS.
        * date: data nel formato YYYmmdd
        * time: ora nel formato HHMM
        * lon: longitudine del centro cella
        * lat: latitudine del centro cella
        * value: valore (None se mancante)
    """
    missing = gribapi.grib_get(gid, "missingValue")
    dataDate = gribapi.grib_get_string(gid, "dataDate")
    dataTime = gribapi.grib_get_string(gid, "dataTime")
    iterid = gribapi.grib_iterator_new(gid, 0)
    items = []
    while True:
        result = gribapi.grib_iterator_next(iterid)
        if not result:
            break
        lat, lon, value = result
        cellid = coords_to_cellid(gid, lon, lat)
        if value == missing:
            value = None

        items.append({
            "cellid": cellid,
            "date": dataDate,
            "time": dataTime,
            "lon": lon,
            "lat": lat,
            "value": value,
        })

    return items


def dump_csv(gid, filename):
    """Scrive i dati del GRIB nel file passato come parametro."""
    with open(filename, "w") as fp:
        writer = csv.DictWriter(fp, ["cellid", "date", "time", "lat", "lon", "value"])
        items = get_items(gid)
        writer.writeheader()
        writer.writerows(items)


def dump_json(gid, filename):
    """Scrive i dati del GRIB nel file passato come parametro."""
    with open(filename, "w") as fp:
        items = get_items(gid)
        json.dump({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [i["lon"], i["lat"]],
                },
                "properties": dict((k, i[k])
                                   for k in ("cellid", "date", "time", "value"))
            } for i in items]
        }, fp)


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
    parser.add_argument("outdir", help="Directory in cui salvare i file")

    args = parser.parse_args()

    credentials = get_credentials(args.client_secret, args.credential, args)
    httpclient = credentials.authorize(httplib2.Http())

    # Salvo il pacco dati GRIB in un file locale
    gribfilename = "erg5.{refdate:%Y%m%d}0000.grib".format(refdate=args.refdate)
    with open(gribfilename, "wb") as fp:
        # Scrivo il pacco dati
        write_erg5_file(fp, httpclient, args.refdate)

    # Faccio il dump dei messaggi GRIB
    with open(gribfilename, "rb") as fp:
        while True:
            gid = gribapi.grib_new_from_file(fp)
            # Quando è None, non ho più messaggi
            if gid is None:
                break
            # Verifico che sia tra i prodotti che mi interessano
            product_name = get_product_name(gid)
            if product_name is not None:
                dump_csv(gid, "{}/{}.csv".format(args.outdir, product_name))
                dump_json(gid, "{}/{}.json".format(args.outdir, product_name))
