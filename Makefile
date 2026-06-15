DATE ?= $(shell TZ=Asia/Seoul date +%F)
REPORT ?= data/reports/$(DATE)/final.md
VIEW_MODEL ?= data/reports/$(DATE)/view_model.json
ANALYSIS_CONTEXT ?= data/reports/$(DATE)/analysis_context.json
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: collect collect-offline view-model analysis-context render-html test clean-day deploy

collect:
	$(PYTHON) -m src.collect --date $(DATE)

collect-offline:
	$(PYTHON) -m src.collect --date $(DATE) --offline

view-model:
	$(PYTHON) -m src.build_view_model --date $(DATE) --output "$(VIEW_MODEL)"

analysis-context:
	$(PYTHON) -m src.build_analysis_context --date $(DATE) --view-model "$(VIEW_MODEL)" --output "$(ANALYSIS_CONTEXT)"

render-html:
	$(PYTHON) -m src.render_html --date $(DATE) --report "$(REPORT)" --view-model "$(VIEW_MODEL)"

test:
	$(PYTHON) -m unittest discover -s tests

clean-day:
	rm -rf "data/incoming/$(DATE)" "data/reports/$(DATE)"

deploy:
	git add docs/ data/
	git commit -m "deploy: update briefing $(DATE)"
	git push origin main
