"""Moduł do obsługi Google Sheets."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

from .utils import parse_distance

logger = logging.getLogger(__name__)


class SheetsManager:
    """Zarządza zapisem i odczytem danych z Google Sheets."""

    def __init__(self):
        """Inicjalizacja menedżera arkuszy."""
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self.iid_cache = set()  # Cache dla szybkiego sprawdzania duplikatów
        self._authorize()

    def _authorize(self):
        """Autoryzacja z Google Sheets używając Service Account."""
        try:
            # Sprawdź czy są dane Service Account w zmiennej środowiskowej
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
            
            if service_account_json:
                # Usuń BOM jeśli istnieje
                if service_account_json.startswith('\ufeff'):
                    service_account_json = service_account_json[1:]
                    logger.info("Removed BOM from GOOGLE_SERVICE_ACCOUNT")
                
                # Użyj Service Account z zmiennej środowiskowej
                service_account_info = json.loads(service_account_json)
                creds = Credentials.from_service_account_info(
                    service_account_info,
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive.file",
                    ],
                )
                logger.info("Authorized via Service Account (from env)")
            else:
                # Fallback: szukaj pliku service_account.json
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                creds_path = os.path.join(project_root, "service_account.json")

                if not os.path.exists(creds_path):
                    raise FileNotFoundError(
                        "Brak danych Service Account. "
                        "Ustaw GOOGLE_SERVICE_ACCOUNT w zmiennych środowiskowych "
                        "lub dodaj plik service_account.json"
                    )

                creds = Credentials.from_service_account_file(
                    creds_path,
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive.file",
                    ],
                )
                logger.info("Authorized via Service Account (from file)")

            self.client = gspread.authorize(creds)

            spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
            if not spreadsheet_id:
                raise ValueError("Brak GOOGLE_SHEETS_SPREADSHEET_ID w .env")

            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            self.worksheet = self.spreadsheet.get_worksheet(0)
            logger.info("Connected to spreadsheet", extra={"title": self.spreadsheet.title})
        except Exception:
            logger.error("Google Sheets authorization failed", exc_info=True)
            raise

    def get_user_history(self, username: str) -> List[Dict]:
        """
        Pobiera historię aktywności użytkownika.

        Args:
            username: Nazwa użytkownika Discord

        Returns:
            Lista słowników z historią aktywności
        """
        try:
            all_records = self.get_all_activities_with_timestamps()
            user_records = [r for r in all_records if r.get("Nick") == username]
            return user_records
        except Exception as e:
            logger.error(
                "Failed to fetch user history", exc_info=True, extra={"username": username}
            )
            return []

    def _normalize_activity_type(self, activity_type: str) -> str:
        """
        Normalizuje typ aktywności do wartości akceptowanych w arkuszu.

        Args:
            activity_type: Typ aktywności wejściowy

        Returns:
            Znormalizowany typ aktywności
        """
        activity_type_lower = activity_type.lower()

        # Mapowanie różnych wariantów na właściwe wartości w arkuszu
        # Format arkusza: Bieganie (Teren), Bieganie (Bieżnia), Pływanie, Rower / Rolki, Spacer / Trekking, Inne Cardio
        activity_mapping = {
            "bieganie_teren": "Bieganie (Teren)",
            "bieganie (teren)": "Bieganie (Teren)",
            "bieganie teren": "Bieganie (Teren)",
            "running": "Bieganie (Teren)",
            "trail running": "Bieganie (Teren)",
            "trail": "Bieganie (Teren)",
            "bieganie_bieznia": "Bieganie (Bieżnia)",
            "bieganie bieżnia": "Bieganie (Bieżnia)",
            "bieżnia": "Bieganie (Bieżnia)",
            "treadmill": "Bieganie (Bieżnia)",
            "bieganie": "Bieganie (Teren)",
            "plywanie": "Pływanie",
            "pływanie": "Pływanie",
            "swimming": "Pływanie",
            "pool": "Pływanie",
            "open water": "Pływanie",
            "rower": "Rower / Rolki",
            "rolki": "Rower / Rolki",
            "rower/rolki": "Rower / Rolki",
            "cycling": "Rower / Rolki",
            "bike": "Rower / Rolki",
            "biking": "Rower / Rolki",
            "spacer": "Spacer / Trekking",
            "trekking": "Spacer / Trekking",
            "spacer/trekking": "Spacer / Trekking",
            "walking": "Spacer / Trekking",
            "hiking": "Spacer / Trekking",
            "cardio": "Inne Cardio",
            "inne cardio": "Inne Cardio",
            "rowing": "Inne Cardio",
            "elliptical": "Inne Cardio",
            "other": "Inne Cardio",
        }

        # Znajdź najlepsze dopasowanie
        for key, value in activity_mapping.items():
            if key in activity_type_lower:
                return value

        # Domyślnie zwróć oryginalną wartość
        return activity_type

    def add_activity(
        self,
        username: str,
        activity_type: str,
        distance: float,
        has_weight: bool = False,
        timestamp: Optional[str] = None,
        message_id: Optional[str] = None,
        message_timestamp: Optional[str] = None,
    ) -> bool:
        """
        Dodaje nową aktywność do arkusza.

        Struktura arkusza (9 kolumn):
        A: Data
        B: Nick
        C: Rodzaj Aktywności
        D: Dystans (km)
        E: Przewyższenie (m) - puste
        F: Obciążenie > 5kg? - TRUE/FALSE
        G: Spec Ops - puste
        H: PUNKTY - puste (obliczane przez arkusz)
        I: IID - Unikalny identyfikator wiadomości (message_timestamp_message_id)

        Args:
            username: Nazwa użytkownika Discord (Nick)
            activity_type: Typ aktywności (musi pasować do listy w arkuszu)
            distance: Dystans w km
            has_weight: Czy ma obciążenie > 5kg (bool)
            timestamp: Znacznik czasu aktywności (domyślnie teraz)
            message_id: ID wiadomości Discord
            message_timestamp: Timestamp wiadomości Discord

        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Buduj IID z timestamp i ID wiadomości
            iid = ""
            if message_timestamp and message_id:
                iid = f"{message_timestamp}_{message_id}"

            # Normalizuj typ aktywności
            normalized_activity = self._normalize_activity_type(activity_type)

            # Struktura zgodna z arkuszem (8 kolumn):
            # A: Data, B: Nick, C: Rodzaj Aktywności, D: Dystans (km),
            # E: Przewyższenie (m), F: Obciążenie > 5kg?, G: Spec Ops, H: PUNKTY

            # Formatuj dystans jako string z kropką dziesiętną (dla polskiego Google Sheets)
            distance_str = str(float(distance)).replace(".", ",")

            row = [
                timestamp,  # A: Data
                username,  # B: Nick
                normalized_activity,  # C: Rodzaj Aktywności
                distance_str,  # D: Dystans (km) - string z przecinkiem dla polskich Sheets
                "",  # E: Przewyższenie (m) - puste
                has_weight,  # F: Obciążenie > 5kg? - checkbox (boolean)
                "",  # G: Spec Ops - puste
                iid,  # I: IID - unikalny identyfikator wiadomości
            ]

            # Znajdź pierwszy pusty wiersz w kolumnach A:H
            all_values = self.worksheet.get_all_values()

            # Sprawdź czy ostatni wiersz w kolumnach A:H jest pusty
            last_row_data = all_values[-1][:8] if all_values else []
            has_data_in_last_row = any(cell.strip() for cell in last_row_data)

            if has_data_in_last_row:
                # Ostatni wiersz ma dane - dodaj nowy wiersz
                next_row = len(all_values) + 1
                # Rozszerz arkusz o jeden wiersz
                self.worksheet.add_rows(1)
            else:
                # Ostatni wiersz jest pusty - użyj go
                next_row = len(all_values)

            # Dodaj dane do zakresu A:I w następnym wierszu (bez kolumny H - formuła)
            # Musimy podzielić na dwa zakresy: A:G (z IID wykluczonym) i I (IID)
            cell_range_ag = f"A{next_row}:G{next_row}"
            self.worksheet.update(cell_range_ag, [row[:7]], value_input_option="USER_ENTERED")
            # Dodaj IID do kolumny I
            if iid:
                self.worksheet.update(f"I{next_row}", [[iid]], value_input_option="USER_ENTERED")

            # Dodaj formułę do kolumny H (PUNKTY) w nowo dodanym wierszu
            last_row = next_row

            # Formuła z polską notacją używająca LET (dokładnie jak w działającym arkuszu)
            formula = f"""=IF(C{last_row}=""; ""; LET(
  aktywnosc; C{last_row};
  dystans; IF(ISNUMBER(D{last_row}); D{last_row}; 0);
  wznios; IF(ISNUMBER(E{last_row}); E{last_row}; 0);
  szpej; F{last_row};
  specOps; G{last_row};

  BazaPkt; IFS(
    aktywnosc="Bieganie (Teren)"; 1000;
    aktywnosc="Bieganie (Bieżnia)"; 800;
    aktywnosc="Pływanie"; 4000;
    aktywnosc="Rower / Rolki"; 300;
    aktywnosc="Spacer / Trekking"; 200;
    aktywnosc="Inne Cardio"; 800;
    TRUE; 0
  );

  MinDystans; IFS(
    aktywnosc="Rower / Rolki"; 6;
    aktywnosc="Spacer / Trekking"; 3;
    TRUE; 0
  );

  MnoznikSzpeju; IF(AND(szpej=TRUE; OR(aktywnosc="Bieganie (Teren)"; aktywnosc="Bieganie (Bieżnia)"; aktywnosc="Spacer / Trekking"; aktywnosc="Inne Cardio")); 1,5; 1);

  BonusWznios; IFERROR(INT(wznios/50)*500; 0);
  
  BonusSpecOps; IF(specOps=TRUE; 2000; 0);

  Wynik; IF(dystans < MinDystans; 0; (dystans * BazaPkt * MnoznikSzpeju) + BonusWznios + BonusSpecOps);

  Wynik
))"""
            self.worksheet.update_acell(f"H{last_row}", formula)

            # Ustaw format komórki H jako NUMBER (żeby nie interpretowało wyniku jako datę)
            self.worksheet.format(
                f"H{last_row}", {"numberFormat": {"type": "NUMBER", "pattern": "0"}}
            )

            # Dodaj IID do cache
            if iid:
                self.iid_cache.add(iid)

            logger.info(
                "Activity added",
                extra={
                    "username": username,
                    "activity_type": normalized_activity,
                    "distance": distance,
                },
            )
            return True
        except Exception as e:
            logger.error("Failed to add activity", exc_info=True, extra={"username": username})
            return False

    def get_user_total_points(self, username: str) -> int:
        """
        Oblicza sumę punktów użytkownika.

        Args:
            username: Nazwa użytkownika Discord

        Returns:
            Suma punktów
        """
        history = self.get_user_history(username)
        total = sum(record.get("Punkty", 0) for record in history)
        return total

    def setup_headers(self):
        """Ustawia nagłówki w arkuszu jeśli nie istnieją."""
        try:
            headers = self.worksheet.row_values(1)
            if not headers or headers[0] != "Data":
                self.worksheet.insert_row(
                    [
                        "Data",
                        "Nick",
                        "Rodzaj Aktywności",
                        "Dystans (km)",
                        "Przewyższenie (m)",
                        "Obciążenie > 5kg?",
                        "Spec Ops",
                        "PUNKTY",
                        "IID",
                    ],
                    index=1,
                )
                logger.info("Headers added to spreadsheet")
        except Exception as e:
            logger.error("Failed to setup headers", exc_info=True)

    def get_all_activities_with_timestamps(self) -> List[Dict]:
        """
        Pobiera wszystkie aktywności z arkusza wraz z datami i nickami.
        Używa get_all_values() aby uniknąć błędnej konwersji liczb przez gspread.

        Returns:
            Lista słowników z aktywnościami
        """
        try:
            all_values = self.worksheet.get_all_values()
            if len(all_values) < 2:
                return []

            headers = all_values[0][:9]  # Weź pierwsze 9 kolumn (z IID)
            records = []

            for row in all_values[1:]:
                if len(row) > 0 and row[0]:  # Pomiń puste wiersze (bez daty)
                    record = {}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            # Dla dystansu używamy parse_distance z utils
                            if header == "Dystans (km)" and row[i]:
                                record[header] = parse_distance(row[i])
                            else:
                                record[header] = row[i]
                        else:
                            record[header] = ""
                    records.append(record)

            return records
        except Exception as e:
            logger.error("Failed to fetch activities", exc_info=True)
            return []

    def build_iid_cache(self):
        """
        Buduje cache wszystkich IID z arkusza dla szybkiego sprawdzania duplikatów.
        Wywołaj na starcie bota.
        """
        try:
            logger.info("Building IID cache from spreadsheet")
            activities = self.get_all_activities_with_timestamps()

            self.iid_cache.clear()
            for activity in activities:
                iid = activity.get("IID", "")
                if iid:
                    self.iid_cache.add(iid)

            logger.info("IID cache built", extra={"entries": len(self.iid_cache)})
        except Exception as e:
            logger.error("Failed to build IID cache", exc_info=True)
            self.iid_cache = set()  # Pusty set w razie błędu

    def activity_exists(self, message_id: str, message_timestamp: str) -> bool:
        """
        Sprawdza czy aktywność już istnieje w cache IID (szybkie sprawdzenie O(1)).

        Args:
            message_id: ID wiadomości Discord
            message_timestamp: Timestamp wiadomości Discord (jako int string)

        Returns:
            True jeśli istnieje (duplikat), False w przeciwnym razie
        """
        try:
            # Buduj IID do sprawdzenia: {timestamp_int}_{message_id}
            iid_to_check = f"{message_timestamp}_{message_id}"

            # Sprawdź w cache (O(1))
            return iid_to_check in self.iid_cache
        except Exception as e:
            logger.error("Failed to check for duplicate", exc_info=True)
            return False
