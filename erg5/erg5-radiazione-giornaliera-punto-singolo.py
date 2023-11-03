# encoding: utf-8

"""Esempio di utilizzo dei dati ERG5.

Questo script permette di scaricare il pacco dati del giorno dal dataset ERG5,
estrarre la radiazione giornaliera e scaricare poi un singolo punto dalla
griglia. Il punto di griglia viene stampato su stdout sotto forma di CSV
"lat,lon,value,distance" (il dato mancante è una stringa vuota).

Per la parte di lettura del file scaricato, viene usata la libreria ecCodes.

Author: Emanuele Di Giacomo <edigiacomo@arpae.it>
License: GPLv3

Copyright (C) 2017-2023 Arpae-SIMC
"""

import argparse

import requests
import eccodes


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
    # None se non lo trova (eccodes.codes_get lancerebbe un'eccezione)
    grib_get_or_none = lambda gid, key: eccodes.codes_get(gid, key) if eccodes.codes_is_defined(gid, key) else None

    with open(filename) as fp:
        # Itero sui messaggi GRIB
        while True:
            gid = eccodes.codes_new_from_file(fp, eccodes.CODES_PRODUCT_GRIB)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("refdate", type=parse_datestring, help="Data di riferimento (e.g. 2017-01-01)")
    parser.add_argument("longitude", type=float, help="Longitudine del punto")
    parser.add_argument("latitude", type=float, help="Latitudine del punto")

    args = parser.parse_args()

    # Salvo il pacco dati GRIB in un file locale
    gribfilename = "erg5.{refdate:%Y%m%d}0000.grib".format(refdate=args.refdate)
    griburl = f"https://dati-simc.arpae.it/opendata/erg5v2/grib/{args.refdate.year}/{gribfilename}"
    with requests.get(griburl, stream=True) as req:
        req.raise_for_status()
        with open(gribfilename, "wb") as fp:
            for chunk in req.iter_content(chunk_size=1024):
                fp.write(chunk)

    # Dal pacco dati appena scritto, estraggo la radiazione giornaliera
    with open(gribfilename, "rb") as fp:
        gid = get_grib_radiation_daily(fp.name)
        # Se è None, vuol dire che non l'ho trovata
        if gid is None:
            raise Exception("Radiazione giornaliera non trovata")
        else:
            # Prendo il valore del missing value
            missing = eccodes.codes_get(gid, "missingValue")
            # Estraggo il punto più vicino (può lanciare un'eccezione se il
            # punto è fuori dalla griglia).
            point = eccodes.codes_find_nearest(gid,
                                               args.latitude,
                                               args.longitude,
                                               is_lsm=False,
                                               npoints=1)
            # Se il valore è un missing, lo sostituisco con una stringa vuota
            if point[0]["value"] == missing:
                point[0]["value"] = ""
            # Stampo il CSV con il risultato
            print("{lat},{lon},{value},{distance}".format(**point[0]))
