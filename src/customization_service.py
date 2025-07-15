import os
import json

class CustomizationService:
    def __init__(self, data_folder='data'):
        self.data_folder = data_folder
        self.settings_file = os.path.join(self.data_folder, 'customization_settings.json')
        self.settings = self._load_settings()

    def _load_settings(self):
        """Load customization settings from a file."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        return {
            'job_description': ''
        }

    def _save_settings(self):
        """Save customization settings to a file."""
        os.makedirs(self.data_folder, exist_ok=True)
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def get_settings(self):
        """Get the current customization settings."""
        return self.settings

    def update_settings(self, job_description):
        """Update and save the customization settings."""
        self.settings['job_description'] = job_description
        self._save_settings()
        return {'success': True} 