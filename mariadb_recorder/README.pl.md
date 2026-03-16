# MariaDB Recorder Backend (Dodatek Home Assistant) — PL

Gotowy do użycia custom add-on dla Home Assistanta, umożliwiający użycie **MariaDB** jako backendu `recorder` zamiast SQLite.

## Jak działa dodatek

Dodatek obsługuje dwa tryby:

1. **`internal_mariadb`**
   - instaluje i uruchamia MariaDB wewnątrz dodatku,
   - inicjalizuje trwały katalog danych (`/data/mysql`),
   - tworzy bazę i dedykowanego użytkownika dla Home Assistanta,
   - zachowuje dane po restartach i aktualizacjach.

2. **`external_mariadb`**
   - korzysta z parametrów połączenia do zewnętrznej MariaDB,
   - waliduje połączenie i dane logowania,
   - generuje gotowy `db_url` dla konfiguracji `recorder`.

## Wymagania

- Home Assistant OS / Supervised (obsługa add-onów).
- Dodane repozytorium custom add-on.
- Dla trybu external: dostępny host MariaDB i poprawne dane logowania.

## Instalacja krok po kroku

1. W Home Assistant przejdź do **Ustawienia → Dodatki → Sklep dodatków → Repozytoria**.
2. Dodaj URL tego repozytorium.
3. Zainstaluj dodatek **MariaDB Recorder Backend**.
4. Uzupełnij konfigurację dodatku (sekcje poniżej).
5. Uruchom dodatek.
6. Skopiuj wygenerowany `db_url` do `configuration.yaml` Home Assistanta (`recorder.db_url`).
7. Zrestartuj Home Assistant Core.

## Konfiguracja

### Tryb `internal_mariadb`

```yaml
mode: internal_mariadb
internal_database: homeassistant
internal_username: homeassistant
internal_password: "MOCNE_HASLO"
internal_port: 3306
charset: utf8mb4
collation: utf8mb4_unicode_ci
ssl_mode: disabled
additional_parameters: ""
log_level: info
```

### Tryb `external_mariadb`

```yaml
mode: external_mariadb
external_host: 192.168.1.50
external_port: 3306
external_database: homeassistant
external_username: ha_recorder
external_password: "MOCNE_HASLO"
charset: utf8mb4
collation: utf8mb4_unicode_ci
ssl_mode: required
additional_parameters: ""
log_level: info
```

### Opis opcji

- `mode`: `internal_mariadb` albo `external_mariadb`
- `internal_*`: używane tylko w trybie internal
- `external_*`: używane tylko w trybie external
- `charset`: kodowanie klienta DB (domyślnie `utf8mb4`)
- `collation`: collation (domyślnie `utf8mb4_unicode_ci`)
- `ssl_mode`: `disabled`, `required`, `verify_ca`, `verify_identity`
- `additional_parameters`: dodatkowe parametry URL (`k=v&k2=v2`)
- `log_level`: poziom logowania dodatku

## Integracja z recorder (Home Assistant)

Dodatek zapisuje pomocniczy plik:

- `/data/recorder_connection.txt`

Plik zawiera gotowy fragment konfiguracji `recorder`.

Przykład do `configuration.yaml`:

```yaml
recorder:
  db_url: mysql://user:password@host:3306/homeassistant?charset=utf8mb4
```

Po zapisaniu konfiguracji zrestartuj Home Assistant Core.

## Ważne ograniczenie techniczne platformy

Home Assistant add-ons **nie wspierają bezpiecznego i w pełni automatycznego** mechanizmu modyfikacji pliku `configuration.yaml` Core oraz kompletnego przełączenia `recorder.db_url` bez udziału użytkownika.

Dlatego dodatek realizuje najlepszy możliwy model półautomatyczny:

- waliduje konfigurację,
- inicjalizuje lokalną bazę (w trybie internal),
- tworzy kompletny `db_url`,
- zapisuje wskazówki i pokazuje zanonimizowany URL w logach.

Ostatni krok (wklejenie `recorder.db_url` do konfiguracji HA) wykonujesz ręcznie.

## Bezpieczeństwo

- Brak hardcoded loginów i haseł.
- Hasła pochodzą wyłącznie z konfiguracji dodatku.
- Logi nie ujawniają hasła (maskowanie).
- W trybie internal tworzony jest dedykowany użytkownik z uprawnieniami tylko do wskazanej bazy.
- Inicjalizacja jest odporna na restarty i częściowe wykonanie.

## Trwałość danych i aktualizacje

- Dane MariaDB (tryb internal) są przechowywane w `/data/mysql` (persistent storage dodatku).
- Restart/aktualizacja dodatku nie usuwa danych.
- Inicjalizacja jest idempotentna (`IF NOT EXISTS`, `ALTER USER`).

## Troubleshooting

1. **Brak połączenia w trybie external**
   - sprawdź host/port,
   - sprawdź login/hasło,
   - sprawdź firewall i `bind-address` w MariaDB.

2. **Home Assistant dalej używa SQLite**
   - sprawdź, czy `configuration.yaml` zawiera `recorder.db_url`,
   - zrestartuj Home Assistant Core.

3. **Problemy z kodowaniem**
   - ustaw `charset=utf8mb4` i `collation=utf8mb4_unicode_ci`.

4. **Błąd startu trybu internal**
   - sprawdź logi dodatku,
   - upewnij się, że hasła nie są puste,
   - sprawdź zajętość portu 3306.

