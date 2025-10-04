from app.main import app
import uvicorn
 
if __name__ == "__main__":
    uvicorn.run(app, host="127.*.*.*", port=8000)