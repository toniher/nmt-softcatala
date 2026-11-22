-- A 63-word paragraph (6 sentences, translated as one batch). Used by tune.sh.
wrk.method = "POST"
wrk.body   = "langpair=en%7Cca&q=The+committee+met+on+Tuesday+to+review+the+annual+budget.+Several+members+raised+concerns+about+the+rising+cost+of+energy.+After+a+long+discussion%2C+they+agreed+to+postpone+the+final+vote+until+next+month.+The+chair+thanked+everyone+for+their+patience.+A+new+proposal+will+be+circulated+to+all+members+before+the+next+meeting.+Public+comments+can+be+sent+by+email+until+Friday."
wrk.headers["Content-Type"] = "application/x-www-form-urlencoded"

done = function(summary, latency, requests)
  local errors = summary.errors.status + summary.errors.connect + summary.errors.read + summary.errors.write + summary.errors.timeout
  io.write(string.format("RESULT %.1f %.0f %.0f %d\n", summary.requests / (summary.duration / 1e6),
           latency:percentile(50) / 1000, latency:percentile(99) / 1000, errors))
end
