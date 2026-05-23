// Set a long-lived cookie that the browser automatically attaches to ALL requests
document.cookie =
  `pf_timezone=${encodeURIComponent(Intl.DateTimeFormat().resolvedOptions().timeZone)}` +
  '; path=/; max-age=31536000; SameSite=Lax'
