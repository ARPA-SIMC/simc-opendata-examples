# ERG5

I dati ERG5 sono pubblicati in due formati:

- Un file al giorno in formato `GRIB2` all'URL
  https://dati-simc.arpae.it/opendata/erg5v2/grib. Ogni file si trova al path
  `YYYY/erg5.YYYYmmddHHMM.grib2`.
- Un file per cella e per anno in formato `CSV` (compresso) all'URL
  https://dati-simc.arpae.it/opendata/erg5v2/timeseries. Ogni file si trova al
  path `IDCELLA/IDCELLA_YYYY.zip`, che contiene due file: uno giornaliero
  `IDCELLA_YYYY_d.csv` e uno orario `IDCELLA_YYYY_h.csv`.


## Singolo punto di radiazione giornaliera da GRIB

Lo script è [erg5-radiazione-giornaliera-punto-singolo.py](erg5-radiazione-giornaliera-punto-singolo.py).

L'esempio di utilizzo è strutturato in:

1. Scaricamento del pacco dati relativo ad un particolare giorno.
2. Lettura dei dati, selezione di un particolare prodotto e estrazione di un
   singolo punto. Usiamo i binding Python di ecCodes. Si veda [la sezione
   dedicata a ecCodes](../eccodes/README.md).


## Dump in CSV e GeoJSON di tutti i dati di uno specifico giorno da GRIB

Lo script è [erg5-dump-data.py](erg5-dump-data.py).

L'esempio di utilizzo è strutturato in:

1. Scaricamento del pacco dati relativo ad un particolare giorno.
2. Dump per ogni messaggio GRIB in CSV e GeoJSON. Il file è selezionato in base
   al match di una serie di chiavi GRIB (si veda la funzione `get_product_name`
   all'interno dello script). Usiamo i binding Python di ecCodes. Si veda [la
   sezione dedicata a ecCodes](../eccodes/README.md).


## Scaricamento dei dati di una singola cella da CSV

Lo script è [erg5-download-csv.py](erg5-download-csv.py), che semplicemente
scarica e scompatta il file zip per la cella e l'anno richiesto da riga di
comando.
