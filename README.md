# aif-hello

Demo service for AIF: a page that calls `helloWorld(id)` (`GET /hello?id=…`) with a
200 ms budget. Timeouts are logged as `ERROR TimeoutError …`, counted by a metric filter,
and the `hello-api-timeouts` alarm notifies AIF, which investigates and opens a draft PR.
Deploys from GitHub Actions on push to `main`.
