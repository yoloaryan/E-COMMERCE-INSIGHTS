"""
Automated Retention Campaign Dispatcher & Multi-Channel Alert Notification System.
Provides Slack Block Kit, Discord Embed, and HTML Email formatting,
cryptographic promo voucher generation, and automated ML watchdog triggers.
"""

import hmac
import hashlib
import time
import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import urllib.request
import urllib.error

# Root path reference
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]


class VoucherGenerator:
    """
    Generates secure, tamper-resistant promotional discount voucher codes.
    """
    @staticmethod
    def generate_voucher_code(prefix: str = "WINBACK", discount_pct: int = 15, length: int = 5) -> str:
        """
        Generates a unique code like WINBACK-15-7X9B2.
        """
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Omits easily confused 0, O, 1, I
        random_suffix = "".join(secrets.choice(alphabet) for _ in range(length))
        clean_prefix = prefix.upper().replace(" ", "")
        return f"{clean_prefix}-{discount_pct}-{random_suffix}"

    @staticmethod
    def calculate_expiration(days_valid: int = 7) -> str:
        """Calculates ISO-8601 timestamp for voucher expiry."""
        exp = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return exp.strftime("%Y-%m-%d %H:%M:%S UTC")


class MessageFormatter:
    """
    Constructs multi-platform payloads for Slack, Discord, and Email.
    """

    @staticmethod
    def build_slack_blocks(
        title: str,
        message: str,
        audience_segment: str,
        audience_size: int,
        revenue_target_gbp: float,
        voucher_code: str,
        discount_pct: int,
        severity: str = "info"
    ) -> Dict[str, Any]:
        """
        Builds a rich Slack Block Kit message payload.
        """
        emoji_map = {"info": "📢", "warning": "⚠️", "critical": "🚨", "success": "🎯"}
        emoji = emoji_map.get(severity, "📢")

        return {
            "text": f"{emoji} {title}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {title}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{message}*\nTarget Cohort: *{audience_segment}* (`{audience_size:,}` accounts)"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Protected Revenue:*\n£{revenue_target_gbp:,.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Incentive Voucher:*\n`{voucher_code}` ({discount_pct}% OFF)"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Retention Studio",
                                "emoji": True
                            },
                            "style": "primary",
                            "url": "http://localhost:8080"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Dispatched by *Nexus Retail AI Campaign Engine* • {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}"
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def build_discord_embed(
        title: str,
        message: str,
        audience_segment: str,
        audience_size: int,
        revenue_target_gbp: float,
        voucher_code: str,
        discount_pct: int,
        severity: str = "info"
    ) -> Dict[str, Any]:
        """
        Builds a rich Discord webhook embed payload.
        """
        color_map = {
            "info": 0x38BDF8,     # Cyan
            "warning": 0xF59E0B,  # Amber
            "critical": 0xEF4444, # Red
            "success": 0x10B981   # Green
        }
        color = color_map.get(severity, 0x38BDF8)

        return {
            "username": "Nexus Retail AI Watchdog",
            "avatar_url": "https://img.icons8.com/fluency/96/artificial-intelligence.png",
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                    "fields": [
                        {"name": "Target Audience", "value": f"{audience_segment} ({audience_size:,} users)", "inline": True},
                        {"name": "Revenue at Risk", "value": f"£{revenue_target_gbp:,.2f}", "inline": True},
                        {"name": "Voucher Code", "value": f"`{voucher_code}` ({discount_pct}% OFF)", "inline": True}
                    ],
                    "footer": {
                        "text": "Nexus Retail AI • Automated Campaign Watchdog"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

    @staticmethod
    def build_html_email(
        customer_name: str,
        discount_pct: int,
        voucher_code: str,
        expires_at: str,
        cta_url: str = "http://localhost:8080"
    ) -> str:
        """
        Generates a responsive HTML email template for retention win-backs.
        """
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 32px 24px; text-align: center; }}
    .body {{ padding: 32px 24px; }}
    .voucher-box {{ background: #f1f5f9; border: 2px dashed #6366f1; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }}
    .voucher-code {{ font-size: 24px; font-weight: 800; letter-spacing: 2px; color: #4338ca; font-family: monospace; }}
    .btn {{ display: inline-block; background: #6366f1; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; margin-top: 12px; }}
    .footer {{ background: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 style="margin: 0; font-size: 22px;">We've Missed You, {customer_name}!</h1>
      <p style="margin: 8px 0 0; opacity: 0.8; font-size: 14px;">Here is an exclusive gift to welcome you back.</p>
    </div>
    <div class="body">
      <p>Hello {customer_name},</p>
      <p>As one of our valued customers, we want to give you an exclusive <strong>{discount_pct}% discount</strong> on your next purchase across our entire catalog.</p>
      
      <div class="voucher-box">
        <div style="font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px;">Your Private Promo Voucher</div>
        <div class="voucher-code">{voucher_code}</div>
        <div style="font-size: 12px; color: #ef4444; margin-top: 6px;">Valid until {expires_at}</div>
      </div>

      <div style="text-align: center;">
        <a href="{cta_url}" class="btn">Shop Now & Apply {discount_pct}% OFF</a>
      </div>
    </div>
    <div class="footer">
      Sent with ❤️ from Nexus Retail AI • Automated Retention System
    </div>
  </div>
</body>
</html>"""


class CampaignRegistry:
    """
    Singleton registry tracking campaign channels, webhook URLs, watchdog rules, and audit stream.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CampaignRegistry, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.channels = {
            "slack": {
                "name": "Slack Incoming Webhook",
                "enabled": True,
                "webhook_url": "",  # Empty = Dry run / simulated
                "icon": "💬",
                "deliveries": 0,
                "status": "SIMULATED_DEV"
            },
            "discord": {
                "name": "Discord Webhook Channel",
                "enabled": True,
                "webhook_url": "",  # Empty = Dry run / simulated
                "icon": "🎮",
                "deliveries": 0,
                "status": "SIMULATED_DEV"
            },
            "email": {
                "name": "Direct Customer Email",
                "enabled": True,
                "smtp_host": "mock://localhost",
                "icon": "✉️",
                "deliveries": 0,
                "status": "SIMULATED_DEV"
            }
        }

        self.watchdogs = {
            "churn_watchdog": {
                "name": "VIP Customer Churn Early Warning",
                "enabled": True,
                "churn_threshold": 0.65,
                "min_spend_gbp": 1000.0,
                "action": "AUTO_DISPATCH_WINBACK",
                "last_triggered_at": None,
                "total_triggers": 0
            },
            "drift_watchdog": {
                "name": "MLOps Feature Drift Alert",
                "enabled": True,
                "psi_threshold": 0.25,
                "action": "ALERT_SLACK_AND_DISCORD",
                "last_triggered_at": None,
                "total_triggers": 0
            },
            "stockout_watchdog": {
                "name": "SKU Inventory Safety Stockout Risk",
                "enabled": True,
                "days_threshold": 7,
                "action": "DISPATCH_SUPPLY_CHAIN_ALERT",
                "last_triggered_at": None,
                "total_triggers": 0
            }
        }

        self.dispatched_campaigns: List[Dict[str, Any]] = []
        self.generated_vouchers: Dict[str, Dict[str, Any]] = {}

    def configure_channel(self, channel: str, webhook_url: Optional[str] = None, enabled: bool = True) -> bool:
        channel = channel.lower()
        if channel in self.channels:
            if webhook_url is not None:
                self.channels[channel]["webhook_url"] = webhook_url.strip()
                self.channels[channel]["status"] = "LIVE_CONNECTED" if webhook_url.startswith("http") else "SIMULATED_DEV"
            self.channels[channel]["enabled"] = enabled
            return True
        return False

    def update_watchdog_rule(self, rule_name: str, enabled: bool) -> bool:
        if rule_name in self.watchdogs:
            self.watchdogs[rule_name]["enabled"] = enabled
            return True
        return False

    def log_dispatch(self, campaign_record: Dict[str, Any]):
        self.dispatched_campaigns.insert(0, campaign_record)
        if len(self.dispatched_campaigns) > 50:
            self.dispatched_campaigns.pop()

    def get_status(self) -> Dict[str, Any]:
        return {
            "channels": self.channels,
            "watchdogs": self.watchdogs,
            "total_campaigns_dispatched": len(self.dispatched_campaigns),
            "total_vouchers_active": len(self.generated_vouchers),
            "total_revenue_protected_gbp": round(sum(c.get("revenue_protected_gbp", 0.0) for c in self.dispatched_campaigns), 2),
            "recent_dispatches": self.dispatched_campaigns[:15]
        }


class CampaignDispatcher:
    """
    Dispatches formatted campaigns across Slack, Discord, Email, and WebSockets.
    """

    @classmethod
    def dispatch_campaign(
        cls,
        campaign_name: str,
        audience_segment: str,
        audience_size: int,
        revenue_target_gbp: float,
        discount_pct: int = 15,
        channels: Optional[List[str]] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes multi-channel campaign dispatch.
        """
        channels = [c.lower() for c in (channels or ["slack", "email"])]
        registry = CampaignRegistry()

        # 1. Generate Promo Voucher
        prefix = audience_segment[:7].upper().replace(" ", "")
        voucher_code = VoucherGenerator.generate_voucher_code(prefix=prefix, discount_pct=discount_pct)
        expires_at = VoucherGenerator.calculate_expiration(days_valid=7)

        registry.generated_vouchers[voucher_code] = {
            "voucher_code": voucher_code,
            "discount_pct": discount_pct,
            "target_segment": audience_segment,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "redeemed": False
        }

        default_msg = f"Automatic retention win-back dispatched offering {discount_pct}% off."
        message = custom_message or default_msg
        results = {}

        # 2. Slack Dispatch
        if "slack" in channels and registry.channels["slack"]["enabled"]:
            slack_payload = MessageFormatter.build_slack_blocks(
                title=f"Retention Campaign: {campaign_name}",
                message=message,
                audience_segment=audience_segment,
                audience_size=audience_size,
                revenue_target_gbp=revenue_target_gbp,
                voucher_code=voucher_code,
                discount_pct=discount_pct,
                severity="success"
            )
            slack_url = registry.channels["slack"]["webhook_url"]
            results["slack"] = cls._post_webhook(slack_url, slack_payload, channel_name="slack")
            registry.channels["slack"]["deliveries"] += 1

        # 3. Discord Dispatch
        if "discord" in channels and registry.channels["discord"]["enabled"]:
            discord_payload = MessageFormatter.build_discord_embed(
                title=f"Retention Campaign: {campaign_name}",
                message=message,
                audience_segment=audience_segment,
                audience_size=audience_size,
                revenue_target_gbp=revenue_target_gbp,
                voucher_code=voucher_code,
                discount_pct=discount_pct,
                severity="success"
            )
            discord_url = registry.channels["discord"]["webhook_url"]
            results["discord"] = cls._post_webhook(discord_url, discord_payload, channel_name="discord")
            registry.channels["discord"]["deliveries"] += 1

        # 4. Email Dispatch (Simulated/Templated)
        if "email" in channels and registry.channels["email"]["enabled"]:
            html_preview = MessageFormatter.build_html_email(
                customer_name="Valued Customer",
                discount_pct=discount_pct,
                voucher_code=voucher_code,
                expires_at=expires_at
            )
            results["email"] = {
                "status": "delivered_simulated",
                "emails_queued": audience_size,
                "voucher_code": voucher_code,
                "html_length": len(html_preview)
            }
            registry.channels["email"]["deliveries"] += audience_size

        # 5. Record Dispatch Telemetry
        now_iso = datetime.now(timezone.utc).isoformat()
        campaign_record = {
            "id": f"camp_{int(time.time() * 1000)}",
            "name": campaign_name,
            "target_segment": audience_segment,
            "audience_size": audience_size,
            "revenue_protected_gbp": round(revenue_target_gbp, 2),
            "discount_pct": discount_pct,
            "voucher_code": voucher_code,
            "expires_at": expires_at,
            "channels_delivered": list(results.keys()),
            "channel_results": results,
            "timestamp": now_iso
        }
        registry.log_dispatch(campaign_record)

        return {
            "status": "success",
            "campaign": campaign_record,
            "message": f"Campaign '{campaign_name}' successfully dispatched across {len(results)} channel(s)."
        }

    @classmethod
    def _post_webhook(cls, url: str, payload: Dict[str, Any], channel_name: str) -> Dict[str, Any]:
        """
        Safely posts JSON payload to webhook URL; falls back to dev simulation if no URL configured.
        """
        if not url or not url.startswith("http"):
            return {
                "status": "simulated_success",
                "mode": "dev_sandbox",
                "channel": channel_name,
                "note": "Payload verified. Configure live webhook URL in Campaign Studio to post to external server."
            }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "NexusRetailAI/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return {
                    "status": "delivered",
                    "http_code": response.status,
                    "channel": channel_name
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "channel": channel_name
            }


class WatchdogEvaluator:
    """
    Evaluates automated operational rules and fires proactive interventions.
    """

    @classmethod
    def evaluate_churn_watchdog(cls, customer_id: Any, churn_prob: float, total_spend_gbp: float) -> Optional[Dict[str, Any]]:
        """
        Checks if customer breaches VIP churn criteria and triggers proactive win-back campaign.
        """
        registry = CampaignRegistry()
        rule = registry.watchdogs["churn_watchdog"]

        if not rule["enabled"]:
            return None

        if churn_prob >= rule["churn_threshold"] and total_spend_gbp >= rule["min_spend_gbp"]:
            rule["total_triggers"] += 1
            rule["last_triggered_at"] = datetime.now(timezone.utc).isoformat()

            # Automatically dispatch VIP win-back intervention
            dispatch_res = CampaignDispatcher.dispatch_campaign(
                campaign_name=f"VIP Churn Safeguard #{customer_id}",
                audience_segment="At-Risk High-Value Accounts",
                audience_size=1,
                revenue_target_gbp=total_spend_gbp,
                discount_pct=20,
                channels=["slack", "email"],
                custom_message=f"CRITICAL: Customer #{customer_id} reached {(churn_prob*100):.1f}% churn probability with £{total_spend_gbp:,.2f} historical spend."
            )
            return {
                "triggered": True,
                "rule": "churn_watchdog",
                "customer_id": customer_id,
                "churn_prob": churn_prob,
                "spend_gbp": total_spend_gbp,
                "dispatch_result": dispatch_res
            }
        return None

    @classmethod
    def evaluate_drift_watchdog(cls, psi_score: float, shifted_features: List[str]) -> Optional[Dict[str, Any]]:
        """
        Alerts operations when MLOps radar detects statistical distribution shift.
        """
        registry = CampaignRegistry()
        rule = registry.watchdogs["drift_watchdog"]

        if not rule["enabled"]:
            return None

        if psi_score >= rule["psi_threshold"]:
            rule["total_triggers"] += 1
            rule["last_triggered_at"] = datetime.now(timezone.utc).isoformat()

            title = "🚨 MLOps Alert: Critical Feature Drift Detected"
            msg = f"Population Stability Index (PSI) reached {psi_score:.3f} (threshold: {rule['psi_threshold']}). Affected features: {', '.join(shifted_features[:3])}."

            results = {}
            if registry.channels["slack"]["enabled"]:
                slack_payload = MessageFormatter.build_slack_blocks(
                    title=title,
                    message=msg,
                    audience_segment="ML Engineering Team",
                    audience_size=1,
                    revenue_target_gbp=0.0,
                    voucher_code="RETRAIN_REQUIRED",
                    discount_pct=0,
                    severity="critical"
                )
                results["slack"] = CampaignDispatcher._post_webhook(
                    registry.channels["slack"]["webhook_url"], slack_payload, channel_name="slack"
                )

            if registry.channels["discord"]["enabled"]:
                discord_payload = MessageFormatter.build_discord_embed(
                    title=title,
                    message=msg,
                    audience_segment="ML Engineering Team",
                    audience_size=1,
                    revenue_target_gbp=0.0,
                    voucher_code="RETRAIN_REQUIRED",
                    discount_pct=0,
                    severity="critical"
                )
                results["discord"] = CampaignDispatcher._post_webhook(
                    registry.channels["discord"]["webhook_url"], discord_payload, channel_name="discord"
                )

            return {
                "triggered": True,
                "rule": "drift_watchdog",
                "psi_score": psi_score,
                "shifted_features": shifted_features,
                "channel_results": results
            }
        return None
