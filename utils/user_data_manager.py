import json
from pathlib import Path

class UserDataManager:
    def __init__(self):
        self.config_dir = Path.home() / ".darkpdf"
        self.settings_file = self.config_dir / "settings.json"
        
        # Default application state
        self.data = {
            "recent_files": [], # List of file paths
            "last_read_pages": {}, # file path -> page index
            "notes": {}, # file path -> { page_index: "note text" }
            "theme": {
                "dark_mode": False,
                "brightness": 1.0,
                "contrast": 1.0
            }
        }
        self.load()

    def get_recent_files(self):
        """Returns list of recent files, filtering out any that no longer exist on disk."""
        existing_files = []
        for f in self.data["recent_files"]:
            if Path(f).exists():
                existing_files.append(f)
            else:
                # Data cleanup for missing files
                self.data["last_read_pages"].pop(f, None)
                self.data["notes"].pop(f, None)
                
        self.data["recent_files"] = existing_files
        self.save()
        return self.data["recent_files"]

    def add_recent_file(self, filepath: str):
        """Adds a file to the top of the recent files list."""
        filepath = str(Path(filepath).resolve())
        if filepath in self.data["recent_files"]:
            self.data["recent_files"].remove(filepath)
        self.data["recent_files"].insert(0, filepath)
        
        # Keep only top 15 recent files
        if len(self.data["recent_files"]) > 15:
            self.data["recent_files"] = self.data["recent_files"][:15]
        self.save()

    def set_last_read_page(self, filepath: str, page_index: int):
        filepath = str(Path(filepath).resolve())
        self.data["last_read_pages"][filepath] = page_index
        self.save()

    def get_last_read_page(self, filepath: str) -> int:
        filepath = str(Path(filepath).resolve())
        return self.data["last_read_pages"].get(filepath, 0)

    def set_note(self, filepath: str, page_index: int, note: str):
        filepath = str(Path(filepath).resolve())
        if filepath not in self.data["notes"]:
            self.data["notes"][filepath] = {}
        # JSON keys are always strings
        self.data["notes"][filepath][str(page_index)] = note
        self.save()

    def get_note(self, filepath: str, page_index: int) -> str:
        filepath = str(Path(filepath).resolve())
        if filepath in self.data["notes"]:
            return self.data["notes"][filepath].get(str(page_index), "")
        return ""

    def get_theme_settings(self):
        return self.data.get("theme", {})

    def set_theme_setting(self, key: str, value):
        if "theme" not in self.data:
            self.data["theme"] = {}
        self.data["theme"][key] = value
        self.save()

    def load(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    # recursively update self.data to handle missing keys in older saves
                    self._update_dict(self.data, loaded_data)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def _update_dict(self, target, source):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._update_dict(target[k], v)
            else:
                target[k] = v

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temp_file = self.settings_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            # Atomic rename to prevent corruption on crash
            temp_file.replace(self.settings_file)
        except Exception as e:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass
            print(f"Error saving settings: {e}")
