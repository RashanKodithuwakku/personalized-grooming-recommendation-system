# Component 3 Flutter client

Manual facial-profile client for the existing FastAPI style-ranking backend on port **8010**. It does not run CatBoost or recompute hybrid scores.

Port 8000 is a different application and is not the default for this client.

## Run the backend

From `backend/`:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Bind `0.0.0.0` if a phone or emulator must reach this machine. Loopback-only CORS is enabled for Flutter **web** on `localhost` / `127.0.0.1` (any port). Restart the Component 3 process after changing CORS. Do not stop other applications that already use a port.

## Run Flutter

From `Frontend/`:

```powershell
flutter pub get
flutter run -d windows --dart-define=API_BASE_URL=http://127.0.0.1:8010
```

| Target | Base URL |
|--------|----------|
| Windows, desktop, web on this PC | `http://127.0.0.1:8010` |
| Android emulator | `http://10.0.2.2:8010` |
| Physical phone | `http://<this-PC-LAN-address>:8010` |

The Android default is the emulator host. A physical phone must use the PC LAN address; `localhost` on the phone is the phone. Change the app-bar URL and choose Apply and retry. The status is Ready only when `/health/ready` reports `ready: true` for the Component 3 service.

Debug and profile Android builds allow cleartext HTTP for this local API. Release Android builds do not.

`flutter test` includes `test/live_api_test.dart`. Those checks call `http://127.0.0.1:8010` and skip when Component 3 is not live there. A skip is not a passing live integration.

## Screens

Profile → Results → Compare → System → Evaluation.

Demo profiles are the verified example JSON files. Confidence presets are manual inputs (`confidence_source=manual`), not detector measurements.

## Evaluation asset

`assets/evaluation/gender_evaluation.csv` is a byte copy of `backend/models/gender_evaluation.csv`. See `assets/evaluation/PROVENANCE.txt`. The screen does not call a new backend endpoint.

## Future upstream profile

`AppController.applyUpstreamProfile` accepts the same profile map Component 2 would send. Image analysis is not implemented here.
