
if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app='main:app', host="10.98.162.9", port=8080, reload=False)
    uvicorn.run(app='main:app', host="127.0.0.1", port=8080, reload=False)
