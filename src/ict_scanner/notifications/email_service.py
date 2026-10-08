import logging
import aiosmtplib
from email.message import EmailMessage
from jinja2 import Template
from ict_scanner.config.settings import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; background-color: #fafafa;">
  <div style="background-color: #111827; color: #ffffff; padding: 12px 16px; border-radius: 6px;">
    <h2 style="margin: 0; font-size: 18px;">ICT Trade Alert: {{symbol}} ({{direction}})</h2>
  </div>
  <div style="margin: 20px 0; background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #eee;">
    <p><strong>Session:</strong> {{session_name}}</p>
    <p><strong>AI Probability Score:</strong> <span style="font-size: 18px; color: #10b981; font-weight: bold;">{{probability_score}}%</span></p>
    <hr style="border: 0; border-top: 1px solid #f0f0f0;" />
    <table style="width: 100%; font-size: 14px; text-align: left;">
      <tr><td><strong>Entry:</strong> {{entry_price}}</td><td><strong>SL:</strong> {{stop_loss}}</td></tr>
      <tr><td><strong>TP:</strong> {{take_profit}}</td><td><strong>R:R:</strong> 1:{{rr_ratio}}</td></tr>
    </table>
  </div>
  <div style="background-color: #ffffff; padding: 16px; border-radius: 6px; border: 1px solid #eee;">
    <h4 style="margin-top: 0;">AI Technical Thesis:</h4>
    <p style="font-size: 14px; line-height: 1.5; color: #374151;">{{thesis}}</p>
    <h4 style="margin-top: 10px; color: #b91c1c;">Invalidation Condition:</h4>
    <p style="font-size: 14px; color: #b91c1c;">{{invalidation}}</p>
  </div>
  <p style="font-size: 11px; color: #9ca3af; text-align: center; margin-top: 20px;">Automated 24/7 Scanner Cloud Node &bull; Generated at {{timestamp_utc}} UTC &bull; Not financial advice</p>
</div>
"""

class EmailNotifier:
    def __init__(self):
        self.template = Template(EMAIL_TEMPLATE, autoescape=True)

    async def send_alert(self, setup: dict, ai_evaluation: dict) -> bool:
        if not settings.smtp_host or not settings.smtp_user or not settings.alert_recipient_email:
            logger.warning("Email credentials not configured. Email alert logged but not sent.")
            return True
            
        html_content = self.template.render(
            symbol=setup.get('symbol'),
            direction=setup.get('direction'),
            session_name=setup.get('session_name'),
            probability_score=ai_evaluation.get('probability_score'),
            entry_price=round(setup.get('entry_price', 0), 5),
            stop_loss=round(setup.get('stop_loss', 0), 5),
            take_profit=round(setup.get('take_profit', 0), 5),
            rr_ratio=round(setup.get('rr_ratio', 0), 2),
            thesis=ai_evaluation.get('thesis'),
            invalidation=ai_evaluation.get('invalidation_rule', ai_evaluation.get('invalidation')),
            timestamp_utc=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        )

        msg = EmailMessage()
        msg['Subject'] = f"ICT Alert: {setup.get('symbol')} {setup.get('direction')}"
        msg['From'] = settings.smtp_user
        msg['To'] = settings.alert_recipient_email
        msg.set_content("Please enable HTML viewing.")
        msg.add_alternative(html_content, subtype='html')

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_pass,
                use_tls=(settings.smtp_port == 465),
                start_tls=(settings.smtp_port == 587),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Email alert: {e}")
            return False
