# Multiplayer Trivia Competition

## Start the Backend Server

From the project root:

```powershell
cd Backend
.\.venv\Scripts\activate
python server.py
```

The backend server runs on `http://localhost:8080`.

If dependencies are not installed yet:

```powershell
cd Backend
pip install -r requirements.txt
```

## Start the Frontend

Open a second terminal from the project root:

```powershell
cd Frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:8081`.
