# Geographic data

The globe uses the `land-110m.json` topology from
[`world-atlas` 2.0.2](https://github.com/topojson/world-atlas), converted before
being committed to GeoJSON with `topojson-client` 3.1.0.

The underlying 1:110m land geometry comes from
[Natural Earth](https://www.naturalearthdata.com/), whose vector map data is in
the public domain.

The converted GeoJSON is committed with
`land-110m.geojson.sha256` and is served directly from this site. The browser
does not fetch geography from a CDN. Its SHA-256 digest is:

```text
837db91532bb2f632eb822ad1159dbe687316d1e63e931327adcdd0a558f8db6
```

The interactive renderer uses the browser's native WebGL API and has no
third-party runtime dependency. The approved repository artwork remains a
static fallback/background; it is not used as a geographic texture.

The geographic layer is presentation support only. Routes and orientation
points are illustrative, use factual latitude/longitude coordinates, and do
not represent live telemetry, deployments, users, monitoring, or project
authority.
