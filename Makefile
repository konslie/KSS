DATE ?= $(shell TZ=Asia/Seoul date +%F)
REPORT ?= data/reports/$(DATE)/final.md
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: collect collect-offline render-html test clean-day

collect:
	$(PYTHON) -m src.collect --date $(DATE)

collect-offline:
	$(PYTHON) -m src.collect --date $(DATE) --offline

render-html:
	$(PYTHON) -m src.render_html --date $(DATE) --report "$(REPORT)"

test:
	$(PYTHON) -m unittest discover -s tests

clean-day:
	rm -rf "data/incoming/$(DATE)" "data/reports/$(DATE)"
