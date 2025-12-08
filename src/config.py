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
    def search_url(self):
        return self._config['scraper']['search_url']
    
    @property
    def url_prefix(self):
        return self._config['scraper']['url_prefix']
    
    @property
    def curl_cffi_impersonate(self):
        return self._config.get('scraper').get('curl_cffi_impersonate', None)
    
    @property
    def is_random(self) -> bool:
        return self._config['scraper']['random_delays']
    
    @property
    def request_timeout(self):
        return self._config['scraper']['request_timeout']
    
    @property
    def db_path(self):
        return self._config['database']['path']
    
    @property
    def force_resync(self) -> bool:
        return self._config['scraper']['force_resync']
    
    @property
    def scraper_library(self):
        return self._config['scraper']['library']

    @property
    def headless(self) -> bool:
        return self._config.get('scraper').get('headless', False)
    
    @property
    def chromedriver_path(self):
        return self._config.get('scraper').get('chromedriver_path', None)
    
    @property
    def car_options(self):
        return self._config['car_options']
    

config = Config()
