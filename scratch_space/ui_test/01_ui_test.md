# Bugs

## 1

going to
http://localhost:8000/pages/things

2026-03-02 18:46:43.659 | INFO | shelf_mind.webapp.core.middleware:dispatch:161 - [637fda7c-b2ef-46fb-8cfe-a25a3ba88b7c] GET /pages/things from 127.0.0.1
2026-03-02 18:46:43.670 | INFO | shelf_mind.webapp.core.middleware:dispatch:172 - [637fda7c-b2ef-46fb-8cfe-a25a3ba88b7c] GET /pages/things -> 200 (10.18ms)
INFO: 127.0.0.1:41850 - "GET /pages/things HTTP/1.1" 200 OK
2026-03-02 18:46:43.798 | INFO | shelf_mind.webapp.core.middleware:dispatch:161 - [4134d17a-db62-4846-942d-aec3c2f0cabb] GET /pages/things/location-options from 127.0.0.1
INFO: 127.0.0.1:41854 - "POST /pages/things/list HTTP/1.1" 403 Forbidden
2026-03-02 18:46:43.819 | INFO | shelf_mind.webapp.core.middleware:dispatch:172 - [4134d17a-db62-4846-942d-aec3c2f0cabb] GET /pages/things/location-options -> 200 (20.49ms)
INFO: 127.0.0.1:41850 - "GET /pages/things/location-options?location_id= HTTP/1.1" 200 OK

UPDATE1: `POST /pages/things/list` still returns 403 Forbidden
UPDATE2: working

## 2

in
http://localhost:8000/pages/things
clicking `Browse` --> no op

UPDATE1: still no op
UPDATE2: still no op

## 3

in
http://localhost:8000/pages/locations

adding a location

INFO: 127.0.0.1:54670 - "POST /pages/locations/create HTTP/1.1" 403 Forbidden

UPDATE1: still 403 Forbidden
UPDATE2: working

## 4

in
http://localhost:8000/pages/search
clicking `Image Search` --> no op

UPDATE1: still no op
UPDATE2: still no op

## 5

in
http://localhost:8000/pages/search

any query

INFO: 127.0.0.1:51484 - "POST /pages/search/results HTTP/1.1" 403 Forbidden

UPDATE1: still 403 Forbidden
UPDATE2: working
