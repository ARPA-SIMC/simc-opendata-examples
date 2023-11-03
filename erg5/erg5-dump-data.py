# encoding: utf-8

"""Esempio di utilizzo dei dati ERG5.

Questo script permette di scaricare il pacco dati del giorno dal dataset ERG5,
e fare il dump in CSV e GeoJSON dei messaggi GRIB, suddivisi per prodotto e per
istante di riferimento.

I file prodotti hanno path nella forma outdir/prodotto_data_ora.csv e
outdir/prodotto_data_ora.json.

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

Per la parte di lettura del file scaricato, viene usata la libreria eccodes.

Author: Emanuele Di Giacomo <edigiacomo@arpae.it>
License: GPLv3

Copyright (C) 2017-2023 Arpae-SIMC
"""

import argparse
import json
import csv

import eccodes
import requests


def get_product_name(gid):
    """Restituisce il nome del prodotto associato al messaggio GRIB passato come
    parametro. Se non lo trova, restituisce None"""

    # Ci sono solo due "prodotti" definiti.
    products = {
        # Temperatura media oraria osservata a 1.8m dal suolo (K)
        "temp_hourly_avg": {
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
            "lengthOfTimeRange": 1,
            "typeOfProcessedData": 0,
        },
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
    codes_match_key_long = lambda gid, k, v: eccodes.codes_get_long(gid, k) == v if eccodes.codes_is_defined(gid, k) else False

    for name, matchers in products.items():
        if all(codes_match_key_long(gid, key, value)
               for key, value in matchers.items()):
            return name

    return None


def coords_to_cellid(gid, lon, lat):
    """
    Converte le coordinate di un punto nella corrispondente cella ERG5.

    Se il punto è fuori dalla griglia, restituisce None.
    """
    lat0 = eccodes.codes_get_double(gid, "latitudeOfFirstGridPointInDegrees")
    lon0 = eccodes.codes_get_double(gid, "longitudeOfFirstGridPointInDegrees")
    ncol = eccodes.codes_get_long(gid, "Ni")
    nrow = eccodes.codes_get_long(gid, "Nj")
    latstep = eccodes.codes_get(gid, "jDirectionIncrementInDegrees")
    lonstep = eccodes.codes_get(gid, "iDirectionIncrementInDegrees")

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
    missing = eccodes.codes_get(gid, "missingValue")
    dataDate = eccodes.codes_get_string(gid, "dataDate")
    dataTime = eccodes.codes_get_string(gid, "dataTime")
    iterid = eccodes.codes_iterator_new(gid, 0)
    items = []
    while True:
        result = eccodes.codes_iterator_next(iterid)
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


def dump_csv(gid, outdir, prefix):
    """Dump dei dati in CSV. Il path del file CSV è nella forma
    outdir/prefix_data_ora.csv."""
    dataDate = eccodes.codes_get_string(gid, "dataDate")
    dataTime = eccodes.codes_get_string(gid, "dataTime")
    filename = "{}/{}_{}_{}.csv".format(outdir, prefix, dataDate, dataTime)
    with open(filename, "w") as fp:
        writer = csv.DictWriter(fp, ["cellid", "date", "time", "lat", "lon", "value"])
        items = get_items(gid)
        writer.writeheader()
        writer.writerows(items)


def dump_json(gid, outdir, prefix):
    """Dump dei dati in GeoJSON. Il path del file GeoJSON è nella forma
    outdir/prefix_data_ora.json."""
    dataDate = eccodes.codes_get_string(gid, "dataDate")
    dataTime = eccodes.codes_get_string(gid, "dataTime")
    filename = "{}/{}_{}_{}.json".format(outdir, prefix, dataDate, dataTime)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("refdate", type=parse_datestring, help="Data di riferimento (e.g. 2017-01-01)")
    parser.add_argument("outdir", help="Directory in cui salvare i file")

    args = parser.parse_args()

    # Salvo il pacco dati GRIB in un file locale
    gribfilename = "erg5.{refdate:%Y%m%d}0000.grib".format(refdate=args.refdate)
    griburl = f"https://dati-simc.arpae.it/opendata/erg5v2/grib/{args.refdate.year}/{gribfilename}"
    with requests.get(griburl, stream=True) as req:
        req.raise_for_status()
        with open(gribfilename, "wb") as fp:
            for chunk in req.iter_content(chunk_size=1024):
                fp.write(chunk)

    # Faccio il dump dei messaggi GRIB
    with open(gribfilename, "rb") as fp:
        while True:
            gid = eccodes.codes_new_from_file(fp, eccodes.CODES_PRODUCT_GRIB)
            # Quando è None, non ho più messaggi
            if gid is None:
                break
            # Verifico che sia tra i prodotti che mi interessano
            product_name = get_product_name(gid)
            if product_name is not None:
                dump_csv(gid, args.outdir, product_name)
                dump_json(gid, args.outdir, product_name)
