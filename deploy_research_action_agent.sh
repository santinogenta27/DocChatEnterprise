#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Deploy script - Research & Action Agent"
echo
echo "1) Instalando dependencias (incluyendo neo4j opcional y pytest)..."
pip install -r requirements.txt

echo
echo "2) Ejecutando tests de Research & Action Agent..."
pytest -q tests/test_graphrag_and_satgraph.py tests/test_mdp_agent_and_scheduler.py tests/test_research_action_agent_legal_graph.py

echo
echo "✅ Todo OK. El Research & Action Agent está listo para deploy."


