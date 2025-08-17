from app import create_app
#test
app = create_app()

if __name__ == '__main__':
    # Consider using a more robust WSGI server for production
    app.run(debug=True, host='0.0.0.0', port=5001) # Changed port to avoid conflict if old script is running
