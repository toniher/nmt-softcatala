-- One short sentence (~20 words), typical of interactive use. Used by tune.sh.
wrk.method = "POST"
wrk.body   = "langpair=en|ca&q=Hello World, there are people out there, and we should wonder where they go at lunch time today."
wrk.headers["Content-Type"] = "application/x-www-form-urlencoded"

done = function(summary, latency, requests)
  local errors = summary.errors.status + summary.errors.connect + summary.errors.read + summary.errors.write + summary.errors.timeout
  io.write(string.format("RESULT %.1f %.0f %.0f %d\n", summary.requests / (summary.duration / 1e6),
           latency:percentile(50) / 1000, latency:percentile(99) / 1000, errors))
end
