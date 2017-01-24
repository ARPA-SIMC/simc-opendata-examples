# ERG5

I dati ERG5 sono pubblicati quotidianamente su Google Drive in formato `GRIB2`
e raggruppati per giorno. Ogni file è nella forma `erg5.YYYYmmddHHMM.grib2`.


## Singolo punto di radiazione giornaliera

Lo script è [erg5-radiazione-giornaliera-punto-singolo.py](erg5-radiazione-giornaliera-punto-singolo.py).

L'esempio di utilizzo è strutturato in:

1. Scaricamento del pacco dati relativo ad un particolare giorno. Usiamo la
   libreria Python `google-api-python-client` per accedere alla cartella Drive.
   Si veda [la sezione dedicata a Google Drive](../google-drive/README.md) per
   maggiori informazioni sul setup.
2. Lettura dei dati, selezione di un particolare prodotto e estrazione di un
   singolo punto. Usiamo i binding Python delle `grib_api`. Si veda [la sezione
   dedicata alle gribapi](../gribapi/README.md).
