"""Notification system for trade show trend alerts.

Supports Slack webhooks, email (SMTP), and generic webhooks.
Sends alerts when new reports are ready, trends shift, or errors occur.
"""

import json
import logging
import os
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""

    # Slack
    slack_webhook_url: str = ""
    slack_channel: str = ""  # Optional override

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: list[str] = field(default_factory=list)

    # Generic webhook
    webhook_url: str = ""
    webhook_headers: dict = field(default_factory=dict)

    # Controls
    notify_on_report: bool = True
    notify_on_error: bool = True
    notify_on_new_trend: bool = True
    min_trend_score: float = 20.0  # Only notify for high-scoring trends

    def __post_init__(self):
        # Load from environment variables if not set
        if not self.slack_webhook_url:
            self.slack_webhook_url = os.environ.get("TRADESHOW_SLACK_WEBHOOK", "")
        if not self.smtp_host:
            self.smtp_host = os.environ.get("TRADESHOW_SMTP_HOST", "")
        if not self.smtp_user:
            self.smtp_user = os.environ.get("TRADESHOW_SMTP_USER", "")
        if not self.smtp_password:
            self.smtp_password = os.environ.get("TRADESHOW_SMTP_PASSWORD", "")
        if not self.email_from:
            self.email_from = os.environ.get("TRADESHOW_EMAIL_FROM", "")
        if not self.email_to:
            to_str = os.environ.get("TRADESHOW_EMAIL_TO", "")
            if to_str:
                self.email_to = [e.strip() for e in to_str.split(",")]
        if not self.webhook_url:
            self.webhook_url = os.environ.get("TRADESHOW_WEBHOOK_URL", "")

    @property
    def has_slack(self) -> bool:
        return bool(self.slack_webhook_url)

    @property
    def has_email(self) -> bool:
        return bool(self.smtp_host and self.email_to)

    @property
    def has_webhook(self) -> bool:
        return bool(self.webhook_url)

    @property
    def any_enabled(self) -> bool:
        return self.has_slack or self.has_email or self.has_webhook


class NotificationManager:
    """Sends notifications across configured channels."""

    def __init__(self, config: NotificationConfig | None = None):
        self.config = config or NotificationConfig()
        self._session = requests.Session()

        channels = []
        if self.config.has_slack:
            channels.append("Slack")
        if self.config.has_email:
            channels.append("Email")
        if self.config.has_webhook:
            channels.append("Webhook")

        if channels:
            logger.info(f"Notifications enabled: {', '.join(channels)}")
        else:
            logger.info("No notification channels configured. "
                        "Set TRADESHOW_SLACK_WEBHOOK, TRADESHOW_SMTP_HOST, "
                        "or TRADESHOW_WEBHOOK_URL to enable.")

    @property
    def is_enabled(self) -> bool:
        return self.config.any_enabled

    def notify_report_ready(self, report_data: dict):
        """Send notification that a new trend report is available."""
        if not self.config.notify_on_report:
            return

        # Build summary
        trends = report_data.get("global_trends", [])
        total_signals = report_data.get("summary", {}).get("total_signals", 0)
        total_events = report_data.get("summary", {}).get("total_events", 0)

        top_trends_text = ""
        for i, t in enumerate(trends[:5], 1):
            top_trends_text += f"  {i}. {t['title']} (score: {t['score']}, {t['signal_type']})\n"

        # Opportunities
        opps = report_data.get("emerging_opportunities", [])
        opps_text = ""
        for opp in opps[:3]:
            opps_text += f"  - {opp}\n"

        subject = f"Trade Show Trends Report: {total_signals} signals from {total_events} events"

        plain_text = f"""New Trade Show Trend Report Available
{'=' * 50}

Signals Analyzed: {total_signals}
Events Covered: {total_events}

TOP GLOBAL TRENDS:
{top_trends_text}
"""
        if opps_text:
            plain_text += f"EMERGING OPPORTUNITIES:\n{opps_text}\n"

        plain_text += "\nView the full report on your dashboard."

        # Slack format
        slack_blocks = self._build_slack_report_blocks(report_data)

        self._send_all(subject=subject, plain_text=plain_text,
                       slack_blocks=slack_blocks, webhook_data={
                           "event": "report_ready",
                           "summary": report_data.get("summary", {}),
                           "top_trends": trends[:5],
                           "opportunities": opps[:3],
                       })

    def notify_new_high_score_trend(self, trend: dict):
        """Send notification for a new high-scoring trend."""
        if not self.config.notify_on_new_trend:
            return
        if trend.get("score", 0) < self.config.min_trend_score:
            return

        subject = f"High-Impact Trend: {trend['title']} (score: {trend['score']})"
        plain_text = f"""High-Impact Trend Detected
{'=' * 50}

Trend: {trend['title']}
Score: {trend['score']}
Type: {trend.get('signal_type', 'unknown')}
Industries: {', '.join(trend.get('industries', [])[:3])}
Regions: {', '.join(trend.get('regions', [])[:3])}

{trend.get('description', '')}

Keywords: {', '.join(trend.get('keywords', [])[:8])}
"""

        self._send_all(subject=subject, plain_text=plain_text,
                       webhook_data={"event": "new_trend", "trend": trend})

    def notify_error(self, error_message: str, context: str = ""):
        """Send notification about an agent error."""
        if not self.config.notify_on_error:
            return

        subject = f"Trade Show Agent Error: {error_message[:80]}"
        plain_text = f"""Trade Show Agent Error
{'=' * 50}

Error: {error_message}
Context: {context or 'General'}

The agent will retry on the next cycle.
"""

        self._send_all(subject=subject, plain_text=plain_text,
                       webhook_data={"event": "error", "error": error_message,
                                     "context": context})

    def notify_agent_started(self, config_summary: dict):
        """Send notification that the agent has started."""
        subject = "Trade Show Agent Started"
        plain_text = f"""Trade Show Trend Analysis Agent Started
{'=' * 50}

Industries: {config_summary.get('industries', 0)}
Regions: {config_summary.get('regions', 0)}
Seed Shows: {config_summary.get('seed_shows', 0)}
Interval: {config_summary.get('interval_minutes', 30)} minutes
AI Extraction: {'Enabled' if config_summary.get('ai_enabled') else 'Disabled'}
"""

        self._send_all(subject=subject, plain_text=plain_text,
                       webhook_data={"event": "agent_started", **config_summary})

    def _send_all(self, subject: str, plain_text: str,
                  slack_blocks: list | None = None,
                  webhook_data: dict | None = None):
        """Send notification to all configured channels."""
        if self.config.has_slack:
            self._send_slack(subject, plain_text, slack_blocks)
        if self.config.has_email:
            self._send_email(subject, plain_text)
        if self.config.has_webhook:
            self._send_webhook(subject, webhook_data or {"message": plain_text})

    def _send_slack(self, subject: str, plain_text: str,
                    blocks: list | None = None):
        """Send a Slack notification via webhook."""
        try:
            payload = {"text": f"*{subject}*\n{plain_text}"}
            if blocks:
                payload["blocks"] = blocks

            if self.config.slack_channel:
                payload["channel"] = self.config.slack_channel

            resp = self._session.post(
                self.config.slack_webhook_url,
                json=payload,
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning(f"Slack notification failed: {resp.status_code} {resp.text}")
            else:
                logger.info("Slack notification sent")
        except Exception as e:
            logger.warning(f"Slack notification error: {e}")

    def _send_email(self, subject: str, plain_text: str):
        """Send an email notification via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.email_from or self.config.smtp_user
            msg["To"] = ", ".join(self.config.email_to)
            msg.attach(MIMEText(plain_text, "plain"))

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(
                    msg["From"],
                    self.config.email_to,
                    msg.as_string(),
                )
            logger.info(f"Email notification sent to {len(self.config.email_to)} recipients")
        except Exception as e:
            logger.warning(f"Email notification error: {e}")

    def _send_webhook(self, subject: str, data: dict):
        """Send a generic webhook notification."""
        try:
            payload = {
                "subject": subject,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                **data,
            }
            headers = {"Content-Type": "application/json"}
            headers.update(self.config.webhook_headers)

            resp = self._session.post(
                self.config.webhook_url,
                json=payload,
                headers=headers,
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.warning(f"Webhook notification failed: {resp.status_code}")
            else:
                logger.info("Webhook notification sent")
        except Exception as e:
            logger.warning(f"Webhook notification error: {e}")

    def _build_slack_report_blocks(self, report_data: dict) -> list:
        """Build Slack Block Kit message for a trend report."""
        trends = report_data.get("global_trends", [])
        summary = report_data.get("summary", {})

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Trade Show Trend Report"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Signals:* {summary.get('total_signals', 0)}"},
                    {"type": "mrkdwn", "text": f"*Events:* {summary.get('total_events', 0)}"},
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Top Global Trends:*"}
            },
        ]

        for i, t in enumerate(trends[:5], 1):
            emoji = {"emerging": ":new:", "growing": ":chart_with_upwards_trend:",
                     "mature": ":white_check_mark:", "declining": ":chart_with_downwards_trend:"}
            e = emoji.get(t.get("signal_type", ""), ":signal_strength:")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{e} *{i}. {t['title']}* (score: {t['score']})\n"
                            f"_{', '.join(t.get('industries', [])[:2])}_ | "
                            f"_{', '.join(t.get('regions', [])[:2])}_"
                }
            })

        opps = report_data.get("emerging_opportunities", [])
        if opps:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn",
                         "text": "*Emerging Opportunities:*\n" +
                                 "\n".join(f":bulb: {o}" for o in opps[:3])}
            })

        return blocks
