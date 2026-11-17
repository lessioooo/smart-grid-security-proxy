from digital_twin import SmartGridTwin

def comando(target, azione="TRIP_BREAKER", valore="1"): #Dizionario che il proxy invia al digital twin
    return {"target": target, "azione": azione, "valore": valore}


def test_stato_iniziale(): #Stato iniziale di rete: tutti nodi chiusi, ospedale alimentato
    twin = SmartGridTwin()
    assert twin.ospedale_alimentato() is True

    #--------TEST SULLA LOGICA DI RETE---------

def test_apro_solo_nord_ospedale_alimentato(): #Apro solo la sottostazione nord, ospedale alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("sottostazione_nord"))
    assert risposta["status"] == "SUCCESS"
    assert risposta["ospedale_alimentato"] is True

def test_blackout_nord_e_sud(): #Apro sia la sottostazione nord che quella sud, ospedale non alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("sottostazione_nord"))
    assert risposta["status"] == "SUCCESS"
    risposta = twin.esegui_comando(comando("sottostazione_sud"))
    assert risposta["status"] == "SUCCESS"
    assert risposta["ospedale_alimentato"] is False

def test_ripristino(): #Dopo il blackout, chiudo la sud, ospedale alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("sottostazione_nord"))
    assert risposta["status"] == "SUCCESS"
    risposta = twin.esegui_comando(comando("sottostazione_sud"))
    assert risposta["status"] == "SUCCESS"
    risposta = twin.esegui_comando(comando("sottostazione_sud", "TRIP_BREAKER", "0"))
    assert risposta["status"] == "SUCCESS"  
    assert risposta["ospedale_alimentato"] is True

def test_centrale_aperta(): #Apro la centrale, ospedale non alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("centrale"))
    assert risposta["status"] == "SUCCESS"
    assert risposta["ospedale_alimentato"] is False

def test_ospedale_aperto(): #Apro l'ospedale, ospedale non alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("ospedale"))
    assert risposta["status"] == "SUCCESS"
    assert risposta["ospedale_alimentato"] is False

    #--------TEST DI VALIDAZIONE---------

def test_azione_sconosciuta(): #Se ricevo un'azione sconosciuta, essa viene riconosciuta come tale, viene mandato errore specifico e ci si accerta che l'ospedale sia ancora alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("ospedale", azione="PIPPO"))
    assert risposta["status"] == "ERROR"
    assert risposta["codice_errore"] == "AZIONE_SCONOSCIUTA"
    assert twin.stato_nodi()["ospedale"] == "CHIUSO"

def test_valore_non_valido(): #Stesso principio: valore non valido, errore e ci si accerta che l'ospedale sia ancora alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("ospedale", valore = "7"))
    assert risposta["status"] == "ERROR"
    assert risposta["codice_errore"] == "VALORE_NON_VALIDO"
    assert twin.stato_nodi()["ospedale"] == "CHIUSO"

def test_valore_lista(): #Valore che non è una stringa (lista) viene bloccato come campo mancante e poi ci si accerta che l'ospedale sia ancora alimentato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando("ospedale",valore = ["1"]))
    assert risposta["status"] == "ERROR"
    assert risposta["codice_errore"] == "CAMPO_MANCANTE"
    assert twin.stato_nodi()["ospedale"] == "CHIUSO"

def test_nodo_inesistente(): #Se il nodo non esiste, viene mandato errore specifico e ci si accerta che nessun nodo venga toccato
    twin = SmartGridTwin()
    risposta = twin.esegui_comando(comando(target = "pippo"))
    assert risposta["status"] == "ERROR"
    assert risposta["codice_errore"] == "NODO_INESISTENTE"
    assert all (s == "CHIUSO" for s in twin.stato_nodi().values())

def test_json_non_valido(): #Se il json non esiste ('{pippo'), o non è dizionario ('5' e '[1,2]'), il json non è valido
    twin = SmartGridTwin()
    for testo in ['{pippo', '5', '[1, 2]']:
        risposta = twin.processa_json(testo)
        assert risposta["status"] == "ERROR"
        assert risposta["codice_errore"] == "JSON_NON_VALIDO"

def test_json_con_campi_extra(): #Se il json contiene campi extra, essi vengono ignorati e l'azione viene eseguita correttamente
    twin = SmartGridTwin()
    risposta = twin.processa_json('{"mittente": "x", "target": "sottostazione_nord", "azione": "TRIP_BREAKER", "valore": "1", "seq": 1 }')
    assert risposta["status"] == "SUCCESS"
    assert risposta["ospedale_alimentato"] is True

    #--------TEST DI ROBUSTEZZA---------

def test_input_spazzatura_non_crasha(): #Se il twin riceve input strani, manda a schermo sempre ERROR
    twin = SmartGridTwin()
    spazzatura = ['', ' ', 'null', 'true', '"stringa"', '[]', '{}',
                  '{"target": null}', '{"target": 5, "azione": 5, "valore": 5}',
                  '\x00\xff', '{' * 1000, 'a' * 100000]
    for testo in spazzatura:
        risposta = twin.processa_json(testo)
        assert risposta["status"] == "ERROR"

def test_processa_json_non_stringa(): #Se il twin riceve un json che non è una stringa, manda ERROR
    twin = SmartGridTwin()
    assert twin.processa_json(None)["status"] == "ERROR"

def test_json_annidato_profondo(): #Se si prova a mandare un json annidato, il twin non crasha, manda ERROR
    twin = SmartGridTwin()
    assert twin.processa_json('[' * 100000)["status"] == "ERROR"
