# Home Assistant Custom Add-on Repository: MariaDB Recorder Backend (PL)

To repozytorium zawiera gotowy do wdrożenia custom add-on dla Home Assistanta, który pozwala używać MariaDB jako backendu `recorder` zamiast SQLite.

## Co robi dodatek

Dodatek działa w dwóch trybach:

1. **`internal_mariadb`**
   - uruchamia lokalną instancję MariaDB w kontenerze dodatku,
   - inicjalizuje trwały katalog danych,
   - tworzy bazę i użytkownika dla Home Assistanta,
   - utrzymuje bazę po restartach i aktualizacjach dodatku.

2. **`external_mariadb`**
   - używa podanych przez użytkownika parametrów połączenia,
   - sprawdza dostępność zewnętrznej bazy,
   - generuje gotowy `db_url` do sekcji `recorder`.

## Instalacja repozytorium i dodatku

1. W Home Assistant przejdź do **Ustawienia → Dodatki → Sklep dodatków**.
2. Otwórz menu (trzy kropki) → **Repozytoria**.
3. Dodaj URL tego repozytorium.
4. Zainstaluj dodatek **MariaDB Recorder Backend**.

> Przed publikacją ustaw poprawny adres repozytorium w pliku `repository.yaml`.

## Dokumentacja dodatku

Pełna dokumentacja (EN) dla konfiguracji, integracji z recorder, troubleshooting i ograniczeń:
- `mariadb_recorder/README.md`

## Struktura repozytorium

- `repository.yaml` — metadane repozytorium add-onów
- `mariadb_recorder/` — kod dodatku, konfiguracja, skrypty i dokumentacja

