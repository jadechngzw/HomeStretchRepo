#!/bin/zsh
set -eu
cd "${0:A:h:h}"
.venv/bin/python -m pytest tests -q
VW_SYSROOT="$(xcrun --show-sdk-path)"
VW_TMP="$(mktemp -d)"
clang -isysroot "$VW_SYSROOT" -Wall -Wextra -Werror -Ifirmware/src tests/test_session.c firmware/src/session.c firmware/src/config.c -o "$VW_TMP/session"
"$VW_TMP/session"
clang -isysroot "$VW_SYSROOT" -Wall -Wextra -Werror -Ifirmware/src tests/test_charger.c firmware/src/power/charger_policy.c -o "$VW_TMP/charger"
"$VW_TMP/charger"
clang -isysroot "$VW_SYSROOT" -Wall -Wextra -Werror -Wno-misleading-indentation -Ifirmware/src tests/test_ppg.c firmware/src/ppg.c -o "$VW_TMP/ppg"
"$VW_TMP/ppg"
