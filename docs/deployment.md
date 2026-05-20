# Deployment Notes

## Local
```bash
cd d:\Шарага\Кинжа8\Task_21_EventMaster
docker compose up --build -d
```

## Main URLs
- Gateway: `http://localhost:8580`
- Frontend: `http://localhost:5178`
- Gateway Swagger: `http://localhost:8580/docs`

## Verification
```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo workflow
```bash
python scripts/demo_pipeline.py
```
