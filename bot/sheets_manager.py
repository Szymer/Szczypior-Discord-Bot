"""Moduł do obsługi Google Sheets."""

import os
import gspread
from google.oauth2.credentials import Credentials
from datetime import datetime
from typing import Optional, List, Dict


class SheetsManager:
    """Zarządza zapisem i odczytem danych z Google Sheets."""
    
    def __init__(self):
        """Inicjalizacja menedżera arkuszy."""
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self._authorize()
    
    def _authorize(self):
        """Autoryzacja z Google Sheets używając OAuth."""
        try:
            # Znajdź absolutną ścieżkę do roota projektu
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            creds_path = os.path.join(project_root, 'authorized_user.json')

            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    "Brak pliku authorized_user.json. "
                    "Uruchom `python setup_google_auth.py` w głównym folderze."
                )

            creds = Credentials.from_authorized_user_file(
                creds_path,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.file'
                ]
            )
            self.client = gspread.authorize(creds)
            print("✅ Autoryzacja przez OAuth")
            
            spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
            if not spreadsheet_id:
                raise ValueError("Brak GOOGLE_SHEETS_SPREADSHEET_ID w .env")
            
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            self.worksheet = self.spreadsheet.get_worksheet(0)
            print(f"✅ Połączono z arkuszem: {self.spreadsheet.title}")
        except Exception as e:
            print(f"❌ Błąd autoryzacji Google Sheets: {e}")
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
            all_records = self.worksheet.get_all_records()
            user_records = [r for r in all_records if r.get('User') == username]
            return user_records
        except Exception as e:
            print(f"Błąd pobierania historii: {e}")
            return []
    
    def add_activity(
        self,
        username: str,
        activity_type: str,
        distance: float,
        weight: Optional[float] = None,
        elevation: Optional[float] = None,
        points: int = 0,
        comment: str = "",
        timestamp: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> bool:
        """
        Dodaje nową aktywność do arkusza.
        
        Args:
            username: Nazwa użytkownika Discord
            activity_type: Typ aktywności (bieganie, rower, etc.)
            distance: Dystans w km
            weight: Opcjonalne obciążenie w kg
            elevation: Opcjonalne przewyższenie w m
            points: Punkty za aktywność
            comment: Komentarz od Gemini
            timestamp: Znacznik czasu (domyślnie teraz)
            message_id: ID wiadomości Discord
            
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            row = [
                timestamp,
                username,
                activity_type,
                distance,
                weight or "",
                elevation or "",
                points,
                comment,
                message_id or ""
            ]
            
            self.worksheet.append_row(row)
            print(f"✅ Dodano aktywność dla {username}: {activity_type} {distance}km")
            return True
        except Exception as e:
            print(f"❌ Błąd dodawania aktywności: {e}")
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
        total = sum(record.get('Punkty', 0) for record in history)
        return total
    
    def setup_headers(self):
        """Ustawia nagłówki w arkuszu jeśli nie istnieją."""
        try:
            headers = self.worksheet.row_values(1)
            if not headers or headers[0] != 'Data':
                self.worksheet.insert_row(
                    ['Data', 'User', 'Aktywność', 'Dystans (km)', 
                     'Obciążenie (kg)', 'Przewyższenie (m)', 'Punkty', 'Komentarz', 'Message ID'],
                    index=1
                )
                print("✅ Dodano nagłówki do arkusza")
        except Exception as e:
            print(f"Błąd ustawiania nagłówków: {e}")
    
    def get_all_message_ids(self) -> List[str]:
        """
        Pobiera wszystkie Message ID z arkusza.
        
        Returns:
            Lista Message ID
        """
        try:
            all_records = self.worksheet.get_all_records()
            message_ids = [str(r.get('Message ID', '')) for r in all_records if r.get('Message ID')]
            return message_ids
        except Exception as e:
            print(f"Błąd pobierania Message ID: {e}")
            return []
    
    def activity_exists_by_message_id(self, message_id: str) -> bool:
        """
        Sprawdza czy aktywność z danym Message ID już istnieje.
        
        Args:
            message_id: ID wiadomości Discord
            
        Returns:
            True jeśli istnieje, False w przeciwnym razie
        """
        message_ids = self.get_all_message_ids()
        return str(message_id) in message_ids
