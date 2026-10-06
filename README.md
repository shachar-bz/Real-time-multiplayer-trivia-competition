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
npm ci
npm run dev
```

The frontend runs on `http://localhost:8081` and connects to the backend on
`http://localhost:8080`. To use a server somewhere else, copy
`Frontend/.env.example` to `Frontend/.env` and set `NEXT_PUBLIC_SERVER_URL`.

The frontend's structure, scripts and tests are described in
[Frontend/README.md](Frontend/README.md).
