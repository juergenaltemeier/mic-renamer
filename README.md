# Photo/Video Renamer

Desktop-App zum Umbenennen von Bildern/Videos nach Projekt, Tags, Datum, Suffix.
Dieser Satz dient als Test für eine kleine Änderung.

## Setup

1. Python 3.8+ installieren.
2. Virtuelle Umgebung erstellen:
   ```bash
   python -m venv venv
   source venv/bin/activate   # oder Windows: .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt

   ### Some Promts: 
   Ich habe dieses Projekt mit folgender Struktur:
- ui/main_window.py (enthält RenamerApp mit Drag&Drop, Preview, Rename)
- logic/renamer.py (Renamer-Klasse)
- logic/settings.py (ItemSettings)
- ui/components.py (DragDropListWidget, TAGS_INFO)
- utils/file_utils.py

Hier ist der Inhalt von ui/main_window.py:
<kopiere den gesamten Code hier>

Und hier logic/renamer.py:
<Code>

Ich möchte nun hinzufügen: [...]

cd path\to\photo-renamer
>> python -m venv venv                                                                                                                                            
>> .\venv\Scripts\activate
>> pip install --upgrade pip
>> pip install PySide6


python -m py_compile ui/main_window.py                                           
python -m py_compile logic/renamer.py                                                                                                                          
python -m py_compile main.py