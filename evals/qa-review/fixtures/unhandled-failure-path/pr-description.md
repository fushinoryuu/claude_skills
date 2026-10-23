PR: #7
Title: FC-3: Fetch the forecast from the weather service
State: OPEN
Base branch: main
Head branch: fc-3-live-forecast
Changed files: README.md, src/forecast/client.py, tests/test_client.py

Body:
Adds `forecast.client` with `fetch_forecast(city)` and a command line entry point.

- The city is URL-encoded, so names with spaces or accents work.
- The result is formatted with the existing `render_forecast`.
- README shows how to run it.

Tests use a fake response, so they do not call the network. They cover the returned days, the encoded URL, and the printed output.
