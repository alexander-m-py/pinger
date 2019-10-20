DC_YML_PATH := deploy/docker/local/docker-compose.yml
COMPOSE := docker-compose -f $(DC_YML_PATH)

run:
	$(COMPOSE) down
	@echo ...starting pinger dependencies
	$(COMPOSE) run --rm start_dependencies
	@echo ...starting pinger
	$(COMPOSE) up -d pinger

rebuild_and_run:
	$(COMPOSE) down
	@echo ...starting pinger dependencies
	$(COMPOSE) run --rm start_dependencies
	@echo ...rebuilding pinger
	$(COMPOSE) up -d --build pinger

test: rebuild_and_run
	$(COMPOSE) run --rm pinger python3.7 -m unittest discover -p "*test.py" -v

ping:
	$(COMPOSE) run --rm pinger python3.7 icmp_pinger.py
