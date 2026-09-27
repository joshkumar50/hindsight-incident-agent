import json
import logging
import requests
from typing import Dict, Any, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import config
from shared.models import RootCauseAnalysis

logger = logging.getLogger(__name__)

class RemediationWorkflow:
    """
    Handles the post-analysis steps of the intelligent SRE workflow:
    - Sending notifications to Slack
    - Creating a Jira ticket
    - Triggering auto-remediation scripts
    """

    def __init__(self):
        self.slack_url = config.integrations.slack_webhook_url
        self.jira_url = config.integrations.jira_webhook_url
        self.remediation_url = config.integrations.remediation_webhook_url

    def execute(self, rca: RootCauseAnalysis) -> Dict[str, str]:
        """Execute all configured post-analysis actions."""
        results = {}

        if self.slack_url:
            results["slack"] = self._notify_slack(rca)
        else:
            results["slack"] = "skipped (no URL)"

        if self.jira_url:
            results["jira"] = self._create_jira_ticket(rca)
        else:
            results["jira"] = "skipped (no URL)"

        if self.remediation_url:
            results["auto_remediation"] = self._trigger_remediation(rca)
        else:
            results["auto_remediation"] = "skipped (no URL)"

        return results

    def _notify_slack(self, rca: RootCauseAnalysis) -> str:
        try:
            payload = {
                "text": f"🚨 *AI Root Cause Analysis Completed*\n\n"
                        f"*Severity:* {rca.severity.value.upper()}\n"
                        f"*Summary:* {rca.root_cause_summary}\n\n"
                        f"*Top Recommendation:* {rca.recommended_actions[0] if rca.recommended_actions else 'None'}\n"
            }
            resp = requests.post(self.slack_url, json=payload, timeout=5)
            if resp.status_code in (200, 201):
                return "success"
            return f"failed: {resp.status_code}"
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return f"error: {str(e)}"

    def _create_jira_ticket(self, rca: RootCauseAnalysis) -> str:
        try:
            payload = {
                "fields": {
                    "summary": f"[AI RCA] {rca.severity.value.upper()} Incident",
                    "description": f"Detailed Analysis:\n{rca.detailed_analysis}\n\nRecommended Actions:\n" + "\n".join(rca.recommended_actions)
                }
            }
            resp = requests.post(self.jira_url, json=payload, timeout=5)
            if resp.status_code in (200, 201):
                return "success"
            return f"failed: {resp.status_code}"
        except Exception as e:
            logger.error(f"Jira ticket creation failed: {e}")
            return f"error: {str(e)}"

    def _trigger_remediation(self, rca: RootCauseAnalysis) -> str:
        try:
            payload = {
                "analysis_id": rca.analysis_id,
                "actions": rca.recommended_actions,
                "affected_components": rca.affected_components
            }
            resp = requests.post(self.remediation_url, json=payload, timeout=5)
            if resp.status_code in (200, 201, 202):
                return "success"
            return f"failed: {resp.status_code}"
        except Exception as e:
            logger.error(f"Auto-remediation failed: {e}")
            return f"error: {str(e)}"
