# encoding: utf-8

"""Esempio di utilizzo dei dati ERG5.

Questo script permette di scaricare il pacco dati di una cella e di uno specifico anno in formato CSV.

Author: Emanuele Di Giacomo <edigiacomo@arpae.it>
License: GPLv3

Copyright (C) 2023 Arpae-SIMC
"""

import argparse
import io
import zipfile

import requests


def parse_datestring(datestr):
    """Semplice parser per le date nella forma YYYY-mm-dd"""
    from datetime import datetime
    return datetime.strptime(datestr, "%Y-%m-%d")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("refdate", type=parse_datestring, help="Data di riferimento (e.g. 2017-01-01)")
    parser.add_argument("cellid", type=int, help="Id della cella ERG5 da scaricare (e.g. 19)")
    parser.add_argument("outdir", type=str, help="Directory in cui estrarre i file CSV")

    args = parser.parse_args()

    zipurl = f"https://dati-simc.arpae.it/opendata/erg5v2/timeseries/{args.cellid:05d}/{args.cellid:05d}_{args.refdate.year}.zip"
    with requests.get(zipurl, stream=True) as req:
        req.raise_for_status()
        zfile = zipfile.ZipFile(io.BytesIO(req.content))
        for name in zfile.namelist():
            print(f"Trovato file {name}")

        print(f"Salvo i file nella directory {args.outdir}")
        zfile.extractall(path=args.outdir)
