from website import create_app

app, cursor = create_app()

if __name__ == '__main__':
    app.run(debug=True) #rerun website if changes detected. set to false for prod