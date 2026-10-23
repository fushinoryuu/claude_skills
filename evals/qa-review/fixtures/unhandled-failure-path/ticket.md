Key: FC-3
Type: Story
Status: In QA
Summary: Show the live forecast for a city

Description:
The forecast tool can only format data it is given. Make it fetch the forecast for a city from the weather service and print it, so people can run it with just a city name.

Acceptance criteria:
1. `python -m forecast.client <city>` fetches the forecast for that city and prints one line per day.
2. City names with spaces or accents work.
3. The README explains how to run it.

Linked issues: none

Comments:
- Dev (2026-03-23): PR 7 is up for QA.
