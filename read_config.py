import configparser
config = configparser.ConfigParser()
config.read('/opt/tuneforge/config.ini')
print("Ollama URL:", config.get('OLLAMA', 'URL', fallback='Not Set'))
