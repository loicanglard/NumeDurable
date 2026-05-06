from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from backend import create_app

# Create the Flask app after loading environment variables from .env
app = create_app()

if __name__ == "__main__":
    # Respect configuration for DEBUG (do not force True)
    app.run(debug=app.config.get('DEBUG', False))