# Hosting the dashboard on PythonAnywhere (free account)

Live: <https://piyushpatnaik.pythonanywhere.com/>

## Files uploaded

Only what `app.py` needs at runtime, copied to `/home/PiyushPatnaik/odisha-drought-dashboard/`:

```
app.py
dashboard/__init__.py  dashboard/data.py  dashboard/figures.py
assets/style.css
data/clean/odisha_month.csv
data/clean/odisha_district_month.csv
data/clean/geo/odisha_districts.geojson
```

## Web app settings

- Web tab → *Manual configuration*, **Python 3.13**
- Source code: `/home/PiyushPatnaik/odisha-drought-dashboard`
- Force HTTPS: on
- No virtualenv: the packages preinstalled in PythonAnywhere's Python 3.13 image are enough
  (pandas 2.2.2, numpy 2.1.0, plotly 5.24.1, dash 2.18.1, Flask 3.0.3 at the time of deployment).
  The newer pins in `requirements-deploy.txt` are for Render/gunicorn and are not needed here.

## WSGI file

`/var/www/piyushpatnaik_pythonanywhere_com_wsgi.py`:

```python
import os
import sys

path = "/home/PiyushPatnaik/odisha-drought-dashboard"
if path not in sys.path:
    sys.path.insert(0, path)
os.chdir(path)  # data paths are resolved from __file__, but keep cwd at the project root anyway

from app import server as application  # Dash's Flask server
```

Then press **Reload** on the Web tab.

## Updating / keeping it alive

- After changing code or data, upload the changed files again (Files tab or the API) and press **Reload**.
- Free web apps expire: click the **"Run until … from today"** extend button on the Web tab before the
  expiry date shown there, otherwise the site is disabled.
- Errors are logged in `/var/log/piyushpatnaik.pythonanywhere.com.error.log`.
