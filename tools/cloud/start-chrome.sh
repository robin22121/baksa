#!/bin/sh
# 시스템 Chrome을 CDP 모드로 띄운다 (창이 보이는 상태 — 이 창에서 클라우드형 양도박사에 로그인한다).
# 별도 프로필(--user-data-dir)을 쓰므로 평소 Chrome과 독립. 이후 dump-web.mjs가 127.0.0.1:9222로 붙는다.
# Mac:     sh tools/cloud/start-chrome.sh
# Windows: "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-cdp --no-first-run
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.cache/chrome-cdp-baksa" \
  --no-first-run about:blank &
