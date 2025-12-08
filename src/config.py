import json
from pathlib import Path

class Config:
    def __init__(self, config_path=None):
        if config_path is None:
            # Find project root (where config.json lives)
            project_root = Path(__file__).parent
            config_path = project_root / 'config.json'

        with open(config_path, 'r') as f:
            self._config = json.load(f)

    def get(self, *keys):
        value = self._config
        for key in keys:
            value = value[key]
        return value
    
    @property
    def log_dir(self):
        return self._config['logger']['directory']

    @property
    def log_level(self):
        return self._config['logger']['level']
    
    @property
    def log_stderr(self) -> bool:
        return self._config.get('logger', {}).get('stderr', False)
    
    @property
    def get_timezone(self) -> str:
        return self._config.get('timezone')
    

config = Config()
