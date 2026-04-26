# Paradigma Pelletti – Memory Map und JSON-Registermodell

Diese Dokumentation beschreibt die aus der OneNote/PDF-Tabelle extrahierte Memory Map der Paradigma Pelletti Heizung und bereitet sie als unterstützende technische Dokumentation für die Paradigma MQTT Bridge auf.

> **Status:** Reverse-Engineering-Dokumentation. Register mit `??` oder `UNBEKANNT` sind nicht abschließend verifiziert und sollten vor produktivem Schreibzugriff experimentell validiert werden.

---

## 1. Zweck der Memory Map

Die Memory Map beschreibt Registerbereiche der Heizungssteuerung, die über die serielle Schnittstelle gelesen oder geschrieben werden können.  
Jeder Eintrag besteht aus:

| Feld | Bedeutung |
|---|---|
| `area` | Logischer Funktionsbereich, z. B. Heizkreis, Warmwasser, Zirkulation |
| `address` | 16-bit Speicheradresse, bestehend aus High-Byte und Low-Byte |
| `length` | Anzahl der Nutzdatenbytes |
| `name` | Semantischer Name des Parameters |
| `encoding` | Interpretation der Rohdaten |
| `unit` | Physikalische Einheit |
| `scale` | Skalierungsfaktor für Rohwerte |
| `access` | Vorgeschlagene Zugriffsklasse: `read`, `write`, `read_write`, `unknown` |
| `notes` | Zusatzinformationen oder Unsicherheiten |

---

## 2. Grundlegende Datentypen und Umrechnungen

### 2.1 Temperaturwerte

Viele Temperaturwerte sind als Integer in Zehntelgrad kodiert.

```text
T / °C = raw / 10
```

Beispiel:

```text
raw = 215  ->  21.5 °C
```

### 2.2 Temperaturdifferenzen

Temperaturdifferenzen sind ebenfalls meist in Zehntel-Kelvin kodiert.

```text
ΔT / K = raw / 10
```

### 2.3 Zeitwerte in Minuten

Register mit der Einheit Minuten werden direkt interpretiert.

```text
t / min = raw
```

### 2.4 Datumswerte

Datumswerte sind als Anzahl der Tage seit dem 01.01.2000 kodiert.

```text
date = 2000-01-01 + raw days
```

### 2.5 Zeitprogramme

Zeitpunkte innerhalb eines Tages sind in 15-Minuten-Schritten seit Mitternacht kodiert.

```text
minutes_since_midnight = raw * 15
```

Beispiel:

```text
raw = 24  ->  06:00
```

### 2.6 Niveauwerte in Zeitprogrammen

| Rohwert | Bedeutung |
|---:|---|
| `0x00` | Keine Aktion / Aus |
| `0x01` | Heizen |
| `0x02` | Komfort |
| `0x03` | Absenken |

---

## 3. Speicherbereiche

## 3.1 Data Dictionary

| Adresse | Länge | Inhalt | Interpretation |
|---|---:|---|---|
| `00 00` | 2 | Unbekannt | Funktion noch nicht identifiziert |

---

## 3.2 Heizkreis 1 – Anlagendaten

| Adresse | Länge | Name | Einheit / Kodierung | Hinweise |
|---|---:|---|---|---|
| `00 02` | 1 | Betriebsart HK1 | Enum | `0 = Programm 1`, `1 = Programm 2`, …, `8 = Aus` |
| `00 03` | 2 | Unbekannt | — | Noch nicht identifiziert |
| `00 05` | 2 | Heiztemperatur HK1 | 0.1 °C | Sollwert |
| `00 07` | 2 | Komforttemperatur HK1 | 0.1 °C | Komfortbetrieb |
| `00 09` | 2 | Absenktemperatur HK1 | 0.1 °C | Absenkbetrieb |
| `00 0B` | 2 | Ferienbeginn | Tage seit 01.01.2000 | Kalenderdatum |
| `00 0D` | 2 | Ferienende | Tage seit 01.01.2000 | Kalenderdatum |
| `00 0F` | 1 | Unbekannt | Enum? | Vermutlich Sommer/Winter-Automatik |
| `00 10` | 2 | Fußpunkt | 0.1 °C | Heizkurvenparameter |
| `00 12` | 2 | Steilheit | 0.1 K/K | Heizkurvenparameter |
| `00 14` | 1 | Unbekannt | — | Noch nicht identifiziert |
| `00 15` | 2 | Max. Vorlauftemperatur | 0.1 °C | Begrenzung |
| `00 17` | 1 | Proportionalbereich | 0.1 K/K | Reglerparameter |
| `00 18` | 1 | Nachstellzeit | min | Reglerparameter |
| `00 19` | 2 | Unbekannt | — | Vermutlich Raumeinfluss oder Raumtemperaturabgleich |
| `00 1B` | 2 | Unbekannt | — | Vermutlich Raumeinfluss oder Raumtemperaturabgleich |
| `00 1D` | 2 | Heizgrenze Heizbetrieb | 0.1 °C | Außentemperaturgrenze |
| `00 1F` | 2 | Heizgrenze Absenken | 0.1 °C | Außentemperaturgrenze |
| `00 21` | 2 | Frostschutz Außentemperatur | 0.1 °C | Frostschutzschwelle |
| `00 23` | 1 | Vorhaltezeit Aufheizen | min | Optimierungsparameter |
| `00 24` | 2 | Unbekannt | — | Noch nicht identifiziert |
| `00 26` | 1 | Überhöhung Kessel | 0.1 K | Differenzwert |
| `00 27` | 1 | Spreizung Heizkreis | 0.1 K | Differenzwert |
| `00 28` | 1 | Minimale Pumpendrehzahl | % | Pumpenparameter |
| `00 29` | 1 | Nachlaufzeit PHK | min | Pumpennachlauf |
| `00 2A` | 1 | Mischerlaufzeit | min | Mischerparameter |
| `00 2B` | 1 | Unbekannt | Enum? | Vermutlich Funktion Kurzschluss TR |

---

## 3.3 Heizzeitprogramme HK1

### Struktur

Jedes Heizzeitprogramm besteht aus:

- 7 Blöcken für Tages-Zeitpunkte
- 7 Blöcken für Tages-Niveaus
- je Block 8 Bytes

Damit enthält jeder Tag acht Schaltpunkte und acht zugehörige Niveaus.

### Heizzeitprogramm 1 HK1

| Bereich | Startadresse | Länge pro Tag | Beschreibung |
|---|---|---:|---|
| Zeiten Montag–Sonntag | `00 2C` | 8 | 15-Minuten-Schritte seit Mitternacht |
| Niveaus Montag–Sonntag | `00 64` | 8 | Niveauwerte `0x00` bis `0x03` |

Tagesadressen:

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `00 2C` | `00 64` |
| Dienstag | `00 34` | `00 6C` |
| Mittwoch | `00 3C` | `00 74` |
| Donnerstag | `00 44` | `00 7C` |
| Freitag | `00 4C` | `00 84` |
| Samstag | `00 54` | `00 8C` |
| Sonntag | `00 5C` | `00 94` |

### Heizzeitprogramm 2 HK1

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `00 9C` | `00 D4` |
| Dienstag | `00 A4` | `00 DC` |
| Mittwoch | `00 AC` | `00 E4` |
| Donnerstag | `00 B4` | `00 EC` |
| Freitag | `00 BC` | `00 F4` |
| Samstag | `00 C4` | `00 FC` |
| Sonntag | `00 CC` | `01 04` |

### Heizzeitprogramm 3 HK1

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `01 0C` | `01 44` |
| Dienstag | `01 14` | `01 4C` |
| Mittwoch | `01 1C` | `01 54` |
| Donnerstag | `01 24` | `01 5C` |
| Freitag | `01 2C` | `01 64` |
| Samstag | `01 34` | `01 6C` |
| Sonntag | `01 3C` | `01 74` |

| Adresse | Länge | Inhalt |
|---|---:|---|
| `01 7C` | 12 | Unbekannt |

---

## 3.4 Heizkreis 2 – Anlagendaten

HK2 ist strukturell analog zu HK1, besitzt aber einen anderen Adressbereich.

| Adresse | Länge | Name | Einheit / Kodierung | Hinweise |
|---|---:|---|---|---|
| `01 88` | 1 | Betriebsart HK2 | Enum | `0 = Programm 1`, `1 = Programm 2`, …, `8 = Aus` |
| `01 89` | 2 | Unbekannt | — | Noch nicht identifiziert |
| `01 8B` | 2 | Heiztemperatur HK2 | 0.1 °C | Sollwert |
| `01 8D` | 2 | Komforttemperatur HK2 | 0.1 °C | Komfortbetrieb |
| `01 8F` | 2 | Absenktemperatur HK2 | 0.1 °C | Absenkbetrieb |
| `01 91` | 2 | Ferienbeginn | Tage seit 01.01.2000 | Kalenderdatum |
| `01 93` | 2 | Ferienende | Tage seit 01.01.2000 | Kalenderdatum |
| `01 95` | 1 | Unbekannt | Enum? | Vermutlich Sommer/Winter-Automatik |
| `01 96` | 2 | Fußpunkt | 0.1 °C | Heizkurvenparameter |
| `01 98` | 2 | Steilheit | 0.1 K/K | Heizkurvenparameter |
| `01 9A` | 1 | Unbekannt | — | Noch nicht identifiziert |
| `01 9B` | 2 | Max. Vorlauftemperatur | 0.1 °C | Begrenzung |
| `01 9D` | 1 | Proportionalbereich | 0.1 K/K | Reglerparameter |
| `01 9E` | 1 | Nachstellzeit | min | Reglerparameter |
| `01 9F` | 2 | Unbekannt | — | Vermutlich Raumeinfluss oder Raumtemperaturabgleich |
| `01 A1` | 2 | Unbekannt | — | Vermutlich Raumeinfluss oder Raumtemperaturabgleich |
| `01 A3` | 2 | Heizgrenze Heizbetrieb | 0.1 °C | Außentemperaturgrenze |
| `01 A5` | 2 | Heizgrenze Absenken | 0.1 °C | Außentemperaturgrenze |
| `01 A7` | 2 | Frostschutz Außentemperatur | 0.1 °C | Frostschutzschwelle |
| `01 A9` | 1 | Vorhaltezeit Aufheizen | min | Optimierungsparameter |
| `01 AA` | 2 | Unbekannt | — | Noch nicht identifiziert |
| `01 AC` | 1 | Überhöhung Kessel | 0.1 K | Differenzwert |
| `01 AD` | 1 | Spreizung Heizkreis | 0.1 K | Differenzwert |
| `01 AE` | 1 | Minimale Pumpendrehzahl | % | Pumpenparameter |
| `01 AF` | 1 | Nachlaufzeit PHK | min | Pumpennachlauf |
| `01 B0` | 1 | Mischerlaufzeit | min | Mischerparameter |
| `01 B1` | 1 | Unbekannt | Enum? | Vermutlich Funktion Kurzschluss TR |

---

## 3.5 Heizzeitprogramme HK2

### Heizzeitprogramm 1 HK2

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `01 B2` | `01 EA` |
| Dienstag | `01 BA` | `01 F2` |
| Mittwoch | `01 C2` | `01 FA` |
| Donnerstag | `01 CA` | `02 02` |
| Freitag | `01 D2` | `02 0A` |
| Samstag | `01 DA` | `02 12` |
| Sonntag | `01 E2` | `02 1A` |

### Heizzeitprogramm 2 HK2

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `02 22` | `02 5A` |
| Dienstag | `02 2A` | `02 62` |
| Mittwoch | `02 32` | `02 6A` |
| Donnerstag | `02 3A` | `02 72` |
| Freitag | `02 42` | `02 7A` |
| Samstag | `02 4A` | `02 82` |
| Sonntag | `02 52` | `02 8A` |

### Heizzeitprogramm 3 HK2

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `02 92` | `02 CA` |
| Dienstag | `02 9A` | `02 D2` |
| Mittwoch | `02 A2` | `02 DA` |
| Donnerstag | `02 AA` | `02 E2` |
| Freitag | `02 B2` | `02 EA` |
| Samstag | `02 BA` | `02 F2` |
| Sonntag | `02 C2` | `02 FA` |

| Adresse | Länge | Inhalt |
|---|---:|---|
| `03 02` | 12 | Unbekannt |

---

## 3.6 Warmwasser

| Adresse | Länge | Name | Einheit / Kodierung | Hinweise |
|---|---:|---|---|---|
| `03 0E` | 2 | Soll 1 | 0.1 °C | Warmwasser-Solltemperatur 1 |
| `03 10` | 2 | Komfort 1 | 0.1 °C | Komforttemperatur 1 |
| `03 12` | 2 | Soll 2 | 0.1 °C | Warmwasser-Solltemperatur 2 |
| `03 14` | 2 | Komfort 2 | 0.1 °C | Komforttemperatur 2 |
| `03 16` | 1 | Differenz | 0.1 K | Schaltdifferenz / Temperaturdifferenz |

---

## 3.7 Warmwasser-Zeitprogramme

### Warmwasser Programm 1

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `03 17` | `03 4F` |
| Dienstag | `03 1F` | `03 57` |
| Mittwoch | `03 27` | `03 5F` |
| Donnerstag | `03 2F` | `03 67` |
| Freitag | `03 37` | `03 6F` |
| Samstag | `03 3F` | `03 77` |
| Sonntag | `03 47` | `03 7F` |

### Warmwasser Programm 2

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `03 87` | `03 BF` |
| Dienstag | `03 8F` | `03 C7` |
| Mittwoch | `03 97` | `03 CF` |
| Donnerstag | `03 9F` | `03 D7` |
| Freitag | `03 A7` | `03 DF` |
| Samstag | `03 AF` | `03 E7` |
| Sonntag | `03 B7` | `03 EF` |

---

## 3.8 Anlagendaten Kessel / Puffer / Zirkulation

| Adresse | Länge | Name | Einheit / Kodierung | Hinweise |
|---|---:|---|---|---|
| `03 F7` | 2 | Nachlaufzeit Pumpe PL/LP | min | Pumpennachlauf |
| `03 F9` | 2 | Max. Puffertemperatur | 0.1 °C | Obergrenze |
| `03 FB` | 2 | Min. Puffertemperatur | 0.1 °C | Untergrenze |
| `03 FD` | 1 | Schaltdifferenz Kessel | 0.1 K | Differenzwert |
| `03 FE` | 1 | Unbekannt | min? | Vermutlich minimale Laufzeit Kessel |
| `03 FF` | 2 | Abschalt-TA Kessel | 0.1 °C | Abschalttemperatur |
| `04 01` | 1 | Min. Drehzahl Pumpe | % | Pumpenparameter |
| `04 02` | 1 | Nachlaufzeit Pumpe PZI | min | Zirkulationspumpe |
| `04 03` | 1 | Sperrzeit Taster | min | Zirkulationslogik |
| `04 04` | 2 | Schaltdifferenz Pumpe | 0.1 K | Differenzwert |

---

## 3.9 Zirkulationsprogramme

### Zirkulationsprogramm 1

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `04 06` | `04 3E` |
| Dienstag | `04 0E` | `04 46` |
| Mittwoch | `04 16` | `04 4E` |
| Donnerstag | `04 1E` | `04 56` |
| Freitag | `04 26` | `04 5E` |
| Samstag | `04 2E` | `04 66` |
| Sonntag | `04 36` | `04 6E` |

### Zirkulationsprogramm 2

| Tag | Zeiten | Niveaus |
|---|---|---|
| Montag | `04 76` | `04 AE` |
| Dienstag | `04 7E` | `04 B6` |
| Mittwoch | `04 86` | `04 BE` |
| Donnerstag | `04 8E` | `04 C6` |
| Freitag | `04 96` | `04 CE` |
| Samstag | `04 9E` | `04 D6` |
| Sonntag | `04 A6` | `04 DE` |

---

## 3.10 Wartung und unbekannte Bereiche

| Adresse | Länge | Inhalt | Interpretation |
|---|---:|---|---|
| `04 E6` | 2 | Wartungstermin | Tage seit 01.01.2000 |
| `04 E8` | 10 | Telefonnummer | BCD-codierte Telefonnummer |
| `04 F2` | 17 | Unbekannt | Nicht identifiziert |
| `05 03` | 5 | Unbekannt | Nicht identifiziert |

---

## 3.11 Anlagendaten Kessel / Puffer 2

| Adresse | Länge | Name | Kodierung |
|---|---:|---|---|
| `05 08` | 1 | Speichertyp | `0 = Optima/Expresso`, `1 = Titan`, `2 = Puffer + ULV`, `3 = Puffer + LP` |
| `05 09` | 2 | Maximaltemperatur WW | 0.1 °C |

---

# 4. Serielles Protokoll

## 4.1 Lesen von Speicherbereichen

Zum Lesen von `<LEN>` Bytes ab Adresse `<AH AL>` wird folgender Telegrammaufbau verwendet:

```text
0A
<PL_LEN>
1C 0C 03
<AH> <AL>
<LEN>
<CHECKSUM>
```

| Feld | Bedeutung |
|---|---|
| `0A` | Message |
| `<PL_LEN>` | Payload-Länge inklusive Checksumme |
| `1C 0C 03` | Kommando: Read Data by Address |
| `<AH> <AL>` | Startadresse |
| `<LEN>` | Anzahl der zu lesenden Bytes |
| `<CHECKSUM>` | Prüfsumme |

Antwort:

```text
FD
<PL_LEN>
0C 03
<AH> <AL>
<LEN>
<DATA...>
<CHECKSUM>
```

---

## 4.2 Schreiben von Speicherbereichen

Zum Schreiben von `<LEN>` Bytes ab Adresse `<AH AL>`:

```text
0A
<PL_LEN>
1D 0C 11 53 45 54
<AH> <AL>
<LEN>
<DATA...>
<CHECKSUM>
```

ASCII-Anteil:

```text
53 45 54 = "SET"
```

Bestätigung:

```text
0A 01 1D 5A
```

---

## 4.3 Sonderfall: Uhrzeit setzen

```text
0A
<PB_LEN>
1D 0C 09 55 48 52
<DH> <DL>
<TH> <TL>
<CHECKSUM>
```

ASCII-Anteil:

```text
55 48 52 = "UHR"
```

| Feld | Bedeutung |
|---|---|
| `<DH DL>` | Tage seit 01.01.2000 |
| `<TH TL>` | Minuten seit Mitternacht |

Bestätigung:

```text
0A 01 1D 5A
```

---

# 5. Vorschlag für ein JSON-Registermodell

## 5.1 Entwurfsziele

Das JSON-Modell soll sowohl für den Register-Handler als auch für die MQTT Bridge nutzbar sein.

Es sollte:

- Register eindeutig über Namen referenzieren
- Adresse und Länge maschinenlesbar halten
- Skalierung und Einheit enthalten
- Enums direkt abbilden
- Zeitprogramme kompakt beschreiben
- Zugriffsschutz ermöglichen
- unbekannte Register explizit kennzeichnen
- MQTT Topic-Strukturen vorbereiten

---

## 5.2 Grundstruktur

```json
{
  "metadata": {
    "device": "Paradigma Pelletti",
    "map_version": "reverse-engineered-2026-04-12",
    "address_format": "uint16_hex",
    "byte_order": "big_endian",
    "value_byte_order": "big_endian",
    "status": "experimental"
  },
  "types": {
    "temp_c_0p1": {
      "encoding": "uint16",
      "scale": 0.1,
      "unit": "degC"
    },
    "delta_k_0p1": {
      "encoding": "uint16",
      "scale": 0.1,
      "unit": "K"
    },
    "minutes_u8": {
      "encoding": "uint8",
      "scale": 1,
      "unit": "min"
    },
    "date_days_since_2000": {
      "encoding": "uint16",
      "epoch": "2000-01-01",
      "unit": "days"
    }
  },
  "registers": []
}
```

---

## 5.3 Einzelregister

Beispiel: Heiztemperatur HK1

```json
{
  "id": "hk1.heiztemperatur",
  "area": "heizkreis_1",
  "address": "0x0005",
  "address_bytes": [0, 5],
  "length": 2,
  "name": "Heiztemperatur HK1",
  "type": "temp_c_0p1",
  "access": "read_write",
  "mqtt": {
    "state_topic": "paradigma/hk1/heiztemperatur/state",
    "command_topic": "paradigma/hk1/heiztemperatur/set"
  }
}
```

---

## 5.4 Enum-Register

Beispiel: Betriebsart HK1

```json
{
  "id": "hk1.betriebsart",
  "area": "heizkreis_1",
  "address": "0x0002",
  "address_bytes": [0, 2],
  "length": 1,
  "name": "Betriebsart HK1",
  "type": "enum",
  "access": "read_write",
  "enum": {
    "0": "programm_1",
    "1": "programm_2",
    "2": "programm_3",
    "8": "aus"
  },
  "mqtt": {
    "state_topic": "paradigma/hk1/betriebsart/state",
    "command_topic": "paradigma/hk1/betriebsart/set"
  }
}
```

---

## 5.5 Unbekannte Register

Unbekannte Register sollten nicht entfernt werden.  
Sie sind für Reverse Engineering wichtig, sollten aber standardmäßig nicht beschreibbar sein.

```json
{
  "id": "hk1.unknown_0003",
  "area": "heizkreis_1",
  "address": "0x0003",
  "address_bytes": [0, 3],
  "length": 2,
  "name": "Unbekanntes Register 00 03",
  "type": "raw",
  "access": "read",
  "verified": false,
  "notes": "Funktion noch nicht identifiziert"
}
```

---

## 5.6 Zeitprogramme als strukturierter Block

Zeitprogramme sollten nicht als 14 unabhängige Registerblöcke modelliert werden, sondern als logischer Block.

```json
{
  "id": "hk1.programm_1",
  "area": "heizkreis_1",
  "kind": "schedule",
  "name": "Heizzeitprogramm 1 HK1",
  "time_resolution_min": 15,
  "entries_per_day": 8,
  "days": {
    "monday": {
      "times_address": "0x002C",
      "levels_address": "0x0064"
    },
    "tuesday": {
      "times_address": "0x0034",
      "levels_address": "0x006C"
    },
    "wednesday": {
      "times_address": "0x003C",
      "levels_address": "0x0074"
    },
    "thursday": {
      "times_address": "0x0044",
      "levels_address": "0x007C"
    },
    "friday": {
      "times_address": "0x004C",
      "levels_address": "0x0084"
    },
    "saturday": {
      "times_address": "0x0054",
      "levels_address": "0x008C"
    },
    "sunday": {
      "times_address": "0x005C",
      "levels_address": "0x0094"
    }
  },
  "level_enum": {
    "0": "none",
    "1": "heating",
    "2": "comfort",
    "3": "reduced"
  },
  "mqtt": {
    "state_topic": "paradigma/hk1/programm_1/state",
    "command_topic": "paradigma/hk1/programm_1/set"
  }
}
```

---

## 5.7 Vollständiger exemplarischer Ausschnitt

```json
{
  "metadata": {
    "device": "Paradigma Pelletti",
    "map_version": "reverse-engineered-2026-04-12",
    "address_format": "uint16_hex",
    "byte_order": "big_endian",
    "value_byte_order": "big_endian",
    "status": "experimental"
  },
  "types": {
    "uint8": {
      "encoding": "uint8",
      "scale": 1
    },
    "uint16": {
      "encoding": "uint16",
      "scale": 1
    },
    "temp_c_0p1": {
      "encoding": "uint16",
      "scale": 0.1,
      "unit": "degC"
    },
    "delta_k_0p1": {
      "encoding": "uint16",
      "scale": 0.1,
      "unit": "K"
    },
    "percent_u8": {
      "encoding": "uint8",
      "scale": 1,
      "unit": "%"
    },
    "minutes_u8": {
      "encoding": "uint8",
      "scale": 1,
      "unit": "min"
    },
    "minutes_u16": {
      "encoding": "uint16",
      "scale": 1,
      "unit": "min"
    },
    "date_days_since_2000": {
      "encoding": "uint16",
      "epoch": "2000-01-01",
      "unit": "days"
    },
    "bcd_phone": {
      "encoding": "bcd",
      "unit": "phone_number"
    },
    "raw": {
      "encoding": "bytes"
    }
  },
  "enums": {
    "operating_mode": {
      "0": "programm_1",
      "1": "programm_2",
      "2": "programm_3",
      "8": "aus"
    },
    "schedule_level": {
      "0": "none",
      "1": "heating",
      "2": "comfort",
      "3": "reduced"
    },
    "storage_type": {
      "0": "optima_expresso",
      "1": "titan",
      "2": "puffer_ulv",
      "3": "puffer_lp"
    }
  },
  "registers": [
    {
      "id": "hk1.betriebsart",
      "area": "heizkreis_1",
      "address": "0x0002",
      "address_bytes": [0, 2],
      "length": 1,
      "name": "Betriebsart HK1",
      "type": "enum",
      "enum_ref": "operating_mode",
      "access": "read_write",
      "verified": true,
      "mqtt": {
        "state_topic": "paradigma/hk1/betriebsart/state",
        "command_topic": "paradigma/hk1/betriebsart/set"
      }
    },
    {
      "id": "hk1.heiztemperatur",
      "area": "heizkreis_1",
      "address": "0x0005",
      "address_bytes": [0, 5],
      "length": 2,
      "name": "Heiztemperatur HK1",
      "type": "temp_c_0p1",
      "access": "read_write",
      "verified": true,
      "mqtt": {
        "state_topic": "paradigma/hk1/heiztemperatur/state",
        "command_topic": "paradigma/hk1/heiztemperatur/set"
      }
    },
    {
      "id": "hk1.komforttemperatur",
      "area": "heizkreis_1",
      "address": "0x0007",
      "address_bytes": [0, 7],
      "length": 2,
      "name": "Komforttemperatur HK1",
      "type": "temp_c_0p1",
      "access": "read_write",
      "verified": true,
      "mqtt": {
        "state_topic": "paradigma/hk1/komforttemperatur/state",
        "command_topic": "paradigma/hk1/komforttemperatur/set"
      }
    },
    {
      "id": "hk1.absenktemperatur",
      "area": "heizkreis_1",
      "address": "0x0009",
      "address_bytes": [0, 9],
      "length": 2,
      "name": "Absenktemperatur HK1",
      "type": "temp_c_0p1",
      "access": "read_write",
      "verified": true,
      "mqtt": {
        "state_topic": "paradigma/hk1/absenktemperatur/state",
        "command_topic": "paradigma/hk1/absenktemperatur/set"
      }
    },
    {
      "id": "ww.soll_1",
      "area": "warmwasser",
      "address": "0x030E",
      "address_bytes": [3, 14],
      "length": 2,
      "name": "Warmwasser Soll 1",
      "type": "temp_c_0p1",
      "access": "read_write",
      "verified": true,
      "mqtt": {
        "state_topic": "paradigma/warmwasser/soll_1/state",
        "command_topic": "paradigma/warmwasser/soll_1/set"
      }
    },
    {
      "id": "anlage.puffer_max_temp",
      "area": "anlage_kessel_puffer_zirkulation",
      "address": "0x03F9",
      "address_bytes": [3, 249],
      "length": 2,
      "name": "Maximale Puffertemperatur",
      "type": "temp_c_0p1",
      "access": "read_write",
      "verified": true,
      "mqtt": {
        "state_topic": "paradigma/anlage/puffer/max_temp/state",
        "command_topic": "paradigma/anlage/puffer/max_temp/set"
      }
    }
  ],
  "schedules": [
    {
      "id": "hk1.programm_1",
      "area": "heizkreis_1",
      "name": "Heizzeitprogramm 1 HK1",
      "time_resolution_min": 15,
      "entries_per_day": 8,
      "level_enum_ref": "schedule_level",
      "access": "read_write",
      "days": {
        "monday": {
          "times_address": "0x002C",
          "levels_address": "0x0064"
        },
        "tuesday": {
          "times_address": "0x0034",
          "levels_address": "0x006C"
        },
        "wednesday": {
          "times_address": "0x003C",
          "levels_address": "0x0074"
        },
        "thursday": {
          "times_address": "0x0044",
          "levels_address": "0x007C"
        },
        "friday": {
          "times_address": "0x004C",
          "levels_address": "0x0084"
        },
        "saturday": {
          "times_address": "0x0054",
          "levels_address": "0x008C"
        },
        "sunday": {
          "times_address": "0x005C",
          "levels_address": "0x0094"
        }
      },
      "mqtt": {
        "state_topic": "paradigma/hk1/programm_1/state",
        "command_topic": "paradigma/hk1/programm_1/set"
      }
    }
  ]
}
```

---

# 6. Empfehlung für die Implementierung

## 6.1 Registerzugriff

Der Register-Handler sollte intern zwei Zugriffspfade anbieten:

```python
value = registers["hk1.heiztemperatur"]
```

und

```python
registers.update_by_address(0x0005, raw_bytes)
```

Damit kann die Bridge sowohl semantisch über Namen arbeiten als auch eingehende Rohdaten anhand der Adresse zuordnen.

---

## 6.2 Schreiben nur für verifizierte Register

Für produktiven Betrieb sollte gelten:

```text
write allowed only if access == "read_write" and verified == true
```

Für Reverse Engineering kann zusätzlich ein Debug- oder Expert-Modus vorgesehen werden.

---

## 6.3 MQTT-Payloads

Für einfache Register:

```json
{
  "value": 21.5,
  "unit": "degC",
  "raw": [0, 215]
}
```

Für Zeitprogramme:

```json
{
  "monday": [
    {
      "time": "06:00",
      "level": "comfort"
    },
    {
      "time": "22:00",
      "level": "reduced"
    }
  ]
}
```

---

# 7. Offene technische Punkte

Die folgenden Punkte sollten bei der weiteren Implementierung geprüft werden:

1. **Byte-Reihenfolge der Mehrbytewerte**  
   Die Adressierung erfolgt eindeutig als `<AH AL>`. Für Nutzdaten wird im JSON-Modell zunächst `big_endian` angenommen.

2. **Vorzeichenbehandlung**  
   Temperaturwerte können eventuell negative Werte enthalten, insbesondere Außentemperatur- oder Frostschutzwerte. Hier muss geprüft werden, ob `int16` statt `uint16` erforderlich ist.

3. **Schreibzugriff absichern**  
   Parameter wie Pumpendrehzahlen, Heizgrenzen und Kesseltemperaturen sollten nur mit Plausibilitätsgrenzen geschrieben werden.

4. **Unbekannte Register erhalten**  
   Unbekannte Speicherbereiche sollten weiter geloggt werden, um Korrelationen mit GUI-Änderungen der Paradigma-Software zu finden.

---

# 8. Vorschlag für Namenskonventionen

## 8.1 Register-IDs

```text
<bereich>.<parameter>
```

Beispiele:

```text
hk1.heiztemperatur
hk1.komforttemperatur
hk2.steilheit
ww.soll_1
anlage.puffer_max_temp
zirkulation.programm_1
```

## 8.2 MQTT Topics

```text
paradigma/<bereich>/<parameter>/state
paradigma/<bereich>/<parameter>/set
```

Beispiele:

```text
paradigma/hk1/heiztemperatur/state
paradigma/hk1/heiztemperatur/set
paradigma/warmwasser/soll_1/state
paradigma/anlage/puffer/max_temp/state
```
