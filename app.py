from backend import create_app

app = create_app()

if __name__ == "__main__":
    # Respect configuration for DEBUG (do not force True)
    app.run(debug=app.config.get('DEBUG', False))