# Contributing

Thanks for improving NPTEL AI Notes Generator.

## Local Checks

Run the checks that match the area you changed:

```bash
cd backend
python -m pytest
python -m alembic upgrade head

cd ../frontend
npm install
npm run build

cd ../caption-service
npm install
npm start
```

## External Services

Automated tests must mock Gemini, YouTube captions, and NPTEL HTTP responses. Do not add tests that spend Gemini quota, download YouTube videos, or depend on live private content.

## Secrets

Do not commit `.env` files, API keys, database credentials, generated private notes, or personal study data.
