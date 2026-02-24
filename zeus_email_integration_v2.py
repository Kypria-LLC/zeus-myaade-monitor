#!/usr/bin/env python3
"""
Zeus Email Integration System v3.0 (LEGAL FORMAT)
For John Kyprianos Estate Case - Protocol Monitoring

v3.0 Changes:
    1. Email body rewritten as formal legal escalation document
    2. Removed all debug/test/system language from email body
    3. Fixed bounced anticorruption.gr -> aead.gr
    4. Added proper sign-off from Stamatina Kyprianos
    5. Added specific case reference numbers (FBI IC3, IRS, EPPO)
    6. Section V international oversight expanded with tracking numbers
    7. Removed "Sent via Zeus" footer and "No more silence" tagline
"""

import os
import sys
import json
import time
import logging
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# =====================================================================
# LOGGING SETUP
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('Zeus')


class ZeusEmailIntegration:
    """
    Zeus Email Integration v3.0 for Greek Protocol Monitoring
    Legal Escalation Document Generator

    Monitors 5 critical protocols with statutory deadlines:
    - 214142: AADE Rebuttal (319/320 smoking gun)
    - ND0113: Ktimatologio refusal + Article 4p3 gaslighting
    - 10690:  Apoketromeni municipality legality review
    - 5534:   DESYP acknowledgment (ZARAVINOU)
    - 051340: AIT.1 ghost refund protocol (5 years dormant)
    """

    def __init__(self) -> None:
        # SMTP Configuration (all from env vars)
        self.smtp_server: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username: str = os.getenv('SMTP_USERNAME', '')
        self.smtp_password: str = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls: bool = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'

        # n8n Webhook URL
        self.n8n_webhook_url: str = os.getenv('N8N_WEBHOOK_URL', '')

        # SMTP retry config
        self.smtp_max_retries: int = int(os.getenv('SMTP_MAX_RETRIES', '3'))
        self.smtp_retry_base_delay: float = float(os.getenv('SMTP_RETRY_DELAY', '2.0'))

        if not self.smtp_username:
            logger.warning(
                "SMTP_USERNAME not set. "
                "Set via: $env:SMTP_USERNAME = 'your@email.com'"
            )

        # Monitored Protocols
        self.MONITORED_PROTOCOLS: Dict[str, Dict] = {
            '214142': {
                'name': 'AADE Rebuttal - 319/320 Smoking Gun',
                'date': '2026-02-11',
                'deadline_days': 60,
                'status': 'ACTIVE - Awaiting response',
                'severity': 'CRITICAL',
                'statutory_basis': 'N.2690/1999 Art.4',
            },
            'ND0113': {
                'name': 'Ktimatologio Refusal + Stop Emailing Us',
                'date': '2026-02-12',
                'deadline_days': 19,
                'status': 'GASLIGHTING - Article 4p3 invoked',
                'severity': 'HIGH',
                'statutory_basis': 'N.2690/1999 Art.5',
            },
            '10690': {
                'name': 'Apoketromeni - Municipality Legality Review',
                'date': '2026-02-15',
                'deadline_days': 30,
                'status': 'ACTIVE - Art.225 N.3852/2010',
                'severity': 'HIGH',
                'statutory_basis': 'N.3852/2010 Art.225',
            },
            '5534': {
                'name': 'DESYP Acknowledgment - ZARAVINOU',
                'date': '2026-02-12',
                'deadline_days': 60,
                'status': 'RECEIVED - MARIA ZARAVINOU confirmation',
                'severity': 'HIGH',
                'statutory_basis': 'N.2690/1999 Art.4',
            },
            '051340': {
                'name': 'AIT.1 Ghost Refund Protocol',
                'date': '2021-01-26',
                'deadline_days': 0,
                'status': 'EXPIRED - 5 years without resolution',
                'severity': 'CRITICAL',
                'statutory_basis': 'EXPIRED',
            },
        }

        # Email Recipients - FIXED: anticorruption.gr -> aead.gr
        self.RECIPIENT_GROUPS: Dict[str, List[str]] = {
            'TIER_1_ENFORCEMENT': [
                'kataggelies@sdoe.gr',
                'sdoe@aade.gr',
                'kefode@aade.gr',
            ],
            'TIER_2_OVERSIGHT': [
                'kataggelies@aead.gr',
                'info@aead.gr',
                'epopteiaota@attica.gr',
                'protokollo@attica.gr',
            ],
            'TIER_3_INTERNATIONAL': [
                'Ana_Wolken@slotkin.senate.gov',
                'info@eppo.europa.eu',
            ],
            'RECORD_KEEPING': [
                os.getenv('RECORD_EMAIL', 'stamatinakyprianou@gmail.com'),
            ],
        }

        # International Case Reference Numbers
        self.CASE_REFERENCES: Dict[str, str] = {
            'FBI_IC3': 'IC3 Ref: eaa5459ac668431abdb33a7f545c3282',
            'IRS_CID': 'IRS F3949A Ref: 477FDA6F',
            'EPPO': 'EPPO Case: PP.00179_2026_EN',
            'SENATE': 'U.S. Senate Foreign Relations Ref: SFK-GR-2026-0211',
            'OLAF': 'OLAF Ref: OF/2026/0322/GR',
        }

        # Agency Pattern Documentation
        self.AGENCY_PATTERNS: Dict[str, str] = {
            'AADE': 'Contradictory checkbox fraud in Form E1 (Protocol 214142) - Line 319 checked NO heirs while Line 320 lists widow',
            'Ktimatologio': 'Invoked Article 4p3 GDPR against legal heir; instructed widow to cease correspondence (Protocol ND0113)',
            'Dimos Spetson': '8 documented errors in death certificate followed by complete administrative silence (Protocol 504)',
            'DESYP': 'Formal acknowledgment received from Maria Zaravinou but no substantive action taken (Protocol 5534)',
            'Cybercrime Unit': 'Complaint redirected to local authorities without investigation; case unilaterally closed',
        }

    def process_zeus_alert(self, alert_data: Dict) -> Optional[Dict]:
        """Process a Zeus alert and generate email configuration."""
        protocol_num = alert_data.get('protocol_num', '')
        if protocol_num not in self.MONITORED_PROTOCOLS:
            logger.error("Unknown protocol: %s", protocol_num)
            return None

        protocol_info = self.MONITORED_PROTOCOLS[protocol_num]
        severity = alert_data.get('severity', protocol_info['severity'])
        subject = self._build_subject(protocol_num, protocol_info, severity)
        body_plain = self._build_email_body(protocol_num, protocol_info, alert_data)
        body_html = self._plain_to_html(body_plain)
        recipients = self._get_recipients(severity)

        return {
            'to': recipients['to'],
            'cc': recipients['cc'],
            'subject': subject,
            'body_plain': body_plain,
            'body_html': body_html,
            'attachments': self._get_attachments(protocol_num),
            'protocol_num': protocol_num,
            'severity': severity,
        }

    def _build_subject(self, protocol_num: str, protocol_info: Dict, severity: str) -> str:
        severity_label = {
            'CRITICAL': '[CRITICAL]',
            'HIGH': '[HIGH]',
            'MEDIUM': '[MEDIUM]',
            'LOW': '[LOW]',
        }.get(severity, '[ALERT]')
        severity_icon = {
            'CRITICAL': '\U0001f534',
            'HIGH': '\U0001f7e1',
            'MEDIUM': '\U0001f7e2',
            'LOW': '\u26ab',
        }.get(severity, '\U0001f7e1')
        short_name = protocol_info['name'].split(' - ')[0]
        return (
            f"\u2696\ufe0f {severity_icon} {severity_label} "
            f"LEGAL NOTIFICATION \u2014 Protocol {protocol_num} "
            f"\u2014 {short_name}"
        )

    def _build_email_body(self, protocol_num: str, protocol_info: Dict, alert_data: Dict) -> str:
        filing_date = datetime.strptime(protocol_info['date'], '%Y-%m-%d')
        if protocol_info['deadline_days'] > 0:
            deadline_date = filing_date + timedelta(days=protocol_info['deadline_days'])
            days_remaining = (deadline_date - datetime.now()).days
            deadline_str = f"{deadline_date.strftime('%B %d, %Y')} ({days_remaining} days remaining)"
        else:
            deadline_str = "EXPIRED - No response received within statutory period"

        sep = "=" * 72
        thin = "-" * 72

        body = f"""
{sep}
FORMAL LEGAL NOTIFICATION
Re: Administrative Protocol {protocol_num}
{sep}

Date of Issue: {datetime.now().strftime('%B %d, %Y')}
Issued By: Stamatina Kyprianos, Widow and Sole Legal Heir
Re: Estate of John (Ioannis) Kyprianos
    Hellenic Navy Veteran | Naturalized U.S. Citizen (May 17, 1976)
    Deceased: June 13, 2021 | Athens, Greece

{thin}
I. SUBJECT OF THIS NOTIFICATION
{thin}

This formal legal notification concerns Protocol {protocol_num}, submitted
to your agency on {filing_date.strftime('%B %d, %Y')}.

Protocol Reference: {protocol_info['name']}
Legal Basis: {protocol_info['statutory_basis']}
Current Status: {protocol_info['status']}
Statutory Response Deadline: {deadline_str}

Your agency has failed to discharge its statutory obligations under
Greek administrative law. This constitutes a material breach of the
duty to respond under Law 2690/1999 (Government Administrative
Procedure Code) and is hereby formally documented.

{thin}
II. STATUTORY DEADLINE - NOTICE OF NON-COMPLIANCE
{thin}

RESPONSE DEADLINE: {deadline_str}
LEGAL BASIS: {protocol_info['statutory_basis']}

Consequences of continued non-compliance:

  1. This non-response is being formally documented as administrative
     failure in accordance with Article 4 of Law 2690/1999.

  2. Escalation materials have been filed with all competent
     oversight authorities, domestic and international.

  3. This correspondence constitutes a legal record and will be
     submitted as documentary evidence in all pending proceedings.

  4. Individual civil servant accountability will be pursued under
     Article 104 of the Greek Civil Service Code.

  5. Documentation has been transmitted to criminal investigation
     authorities in both the United States and the European Union.

{thin}
III. ESTATE PARTICULARS AND LEGAL STANDING
{thin}

Decedent: John (Ioannis) Kyprianos
          U.S. Social Security No.: On file with IRS
          Greek Tax Registration: On file with AADE

Legal Heir: Stamatina Kyprianos (Widow)
            Sole beneficiary under Greek and U.S. law
            Legal standing confirmed under both jurisdictions

Assets Under Dispute:
  - Real Property: Spetses Island (KAEK 05134000000508766)
  - Real Property: Vosporou 14, Keratsini 18755 (KAEK 050681726008)
  - Financial Accounts: National Bank of Greece, Comerica Bank (U.S.)
  - Outstanding Tax Refund: EUR 5,000+ (Protocol 051340 - 5 years unresolved)

{thin}
IV. DOCUMENTED EVIDENCE OF ADMINISTRATIVE MISCONDUCT
{thin}

The following 27 items of documentary evidence have been compiled,
notarized where applicable, and submitted to oversight authorities:

  ITEM 1 - CHECKBOX FRAUD (Protocol 214142)
    AADE Tax Form E1, Line 319: "NO" heirs declared
    AADE Death Certificate, Line 320: Widow listed as heir
    Both submitted same date, same office - constitutes fraud
    Greek Criminal Code Article 216 (document falsification) applies

  ITEM 2 - TIMELINE OBSTRUCTION (Protocol 051340)
    January 25, 2021: Tax representative removed from account
    January 26, 2021: AIT.1 refund protocol activated (next day)
    Account access closed before widow could lawfully intervene
    Pattern consistent with deliberate obstruction of estate rights

  ITEM 3 - ILLEGAL REFUSAL OF ACCESS (Protocol ND0113)
    Ktimatologio refused to provide property records to legal heir
    Invoked Article 4p3 GDPR as pretext - inapplicable to legal heirs
    Official response included instruction to "stop emailing"
    Constitutes violation of Law 2690/1999 Articles 4 and 5

  ITEM 4 - MUNICIPAL NEGLIGENCE (Protocol 10690)
    Death certificate contains 8 documented factual errors
    Dimos (Municipality) of Spetses failed to correct upon request
    Silence continues beyond statutory correction period
    Violates Art. 225 of Law 3852/2010 (Kallikratis Reform)

  ITEM 5 - PATTERN OF COORDINATED NON-RESPONSE
    AADE: Charitable conclusion masking 319/320 checkbox fraud
    Ktimatologio: GDPR misapplication + correspondence cessation
    DESYP: Acknowledgment by Maria Zaravinou; no action thereafter
    Cybercrime Unit: Immediate redirect; case closed without review

{thin}
V. INTERNATIONAL AND DOMESTIC OVERSIGHT - ACTIVE MONITORING
{thin}

This matter is under active monitoring by the following authorities.
All correspondence, responses, and failures to respond are being
shared in real time with each of the following bodies:

  UNITED STATES OF AMERICA:
    Federal Bureau of Investigation, Internet Crime Complaint Center
    {self.CASE_REFERENCES['FBI_IC3']}

    Internal Revenue Service, Criminal Investigation Division
    {self.CASE_REFERENCES['IRS_CID']}

    Office of Senator Elissa Slotkin, U.S. Senate
    {self.CASE_REFERENCES['SENATE']}
    Matter: U.S.-Greece Tax Treaty violations affecting U.S. citizen estate

  EUROPEAN UNION:
    European Public Prosecutor's Office (EPPO)
    {self.CASE_REFERENCES['EPPO']}
    Matter: Cross-border financial misconduct affecting EU citizen rights

    European Anti-Fraud Office (OLAF)
    {self.CASE_REFERENCES['OLAF']}
    Matter: Suspected systemic obstruction of estate rights by public agencies

  HELLENIC REPUBLIC - OVERSIGHT BODIES:
    AEAD (Hellenic Authority for Combating Money Laundering)
    SDOE (Financial Crimes Investigation Unit)
    Apoketromeni - National Transparency Authority
    Ombudsman of the Hellenic Republic (Synigoros tou Politi)

Your agency's response - or failure to respond - to this notification
will be formally reported to each of the above bodies within 5 business
days of the stated response deadline.

{thin}
VI. DOCUMENTED PATTERNS OF NON-COMPLIANCE BY AGENCY
{thin}

The following conduct by Greek public agencies has been formally
documented and reported to oversight authorities:

  AADE: {self.AGENCY_PATTERNS['AADE']}

  Ktimatologio: {self.AGENCY_PATTERNS['Ktimatologio']}

  Dimos Spetson: {self.AGENCY_PATTERNS['Dimos Spetson']}

  DESYP: {self.AGENCY_PATTERNS['DESYP']}

  Cybercrime Unit: {self.AGENCY_PATTERNS['Cybercrime Unit']}

{thin}
VII. REQUIRED ACTION - PROTOCOL {protocol_num}
{thin}

You are hereby required to:

  1. Acknowledge receipt of this notification in writing within
     five (5) business days of receipt.

  2. Provide a substantive written response to Protocol {protocol_num}
     within the statutory deadline of {deadline_str}.

  3. If you dispute jurisdiction or competence, provide written
     reasons and redirect to the competent authority within
     five (5) business days.

Failure to comply will result in:
  - Formal complaint to Synigoros tou Politi (Greek Ombudsman)
  - Individual civil servant misconduct referral to AEAD
  - Transmission of non-response documentation to FBI IC3 and EPPO
  - Legal proceedings in both Greek and U.S. courts

{sep}
SUBMITTED BY:

Stamatina Kyprianos
Widow and Sole Legal Heir - Estate of John Kyprianos
Legal Correspondence Address: stamatinakyprianou@gmail.com

Representing the estate and legal rights of:
John (Ioannis) Kyprianos
Hellenic Navy Veteran | U.S. Navy Service Member
Naturalized U.S. Citizen - May 17, 1976
Deceased: June 13, 2021

Issued: {datetime.now().strftime('%B %d, %Y')}
Reference: ZEUS-{protocol_num}-{datetime.now().strftime('%Y%m%d')}
{sep}
"""
        return body.strip()

    @staticmethod
    def _plain_to_html(plain: str) -> str:
        """Convert plain text to simple HTML."""
        import html as html_mod
        escaped = html_mod.escape(plain)
        escaped = escaped.replace('\n', '<br>\n')
        return (
            '<html><body><pre style="font-family:Courier,monospace;font-size:13px;white-space:pre-wrap;">'
            f'{escaped}'
            '</pre></body></html>'
        )

    def _get_recipients(self, severity: str) -> Dict[str, List[str]]:
        to_list: List[str] = []
        cc_list: List[str] = []
        if severity in ('CRITICAL', 'HIGH'):
            to_list.extend(self.RECIPIENT_GROUPS['TIER_1_ENFORCEMENT'])
            cc_list.extend(self.RECIPIENT_GROUPS['TIER_2_OVERSIGHT'])
            cc_list.extend(self.RECIPIENT_GROUPS['TIER_3_INTERNATIONAL'])
        elif severity == 'MEDIUM':
            to_list.extend(self.RECIPIENT_GROUPS['TIER_1_ENFORCEMENT'])
            cc_list.extend(self.RECIPIENT_GROUPS['TIER_2_OVERSIGHT'])
        else:
            to_list.extend(self.RECIPIENT_GROUPS['TIER_1_ENFORCEMENT'])
            cc_list.extend(self.RECIPIENT_GROUPS['RECORD_KEEPING'])
        return {
            'to': to_list,
            'cc': list(set(cc_list)),
        }

    def _get_attachments(self, protocol_num: str) -> List[str]:
        attachments = [
            'REBUTTAL-AADE-214142-319-320-Feb11-2026.pdf',
            'IRS-Evidence-Summary.pdf',
            'Tax-Treaty-Violations.pdf',
            'MASTER-PROTOCOL-TRACKER-Kyprianos-Case-2026.xlsx',
            'TIMELINE-CORRECTION-AIT1-SMOKING-GUN.md',
        ]
        if protocol_num == '051340':
            attachments.append('protocol-051340.pdf')
        return attachments

    def send_email(self, email_config: Dict, dry_run: bool = True) -> bool:
        if dry_run:
            return self._dry_run_preview(email_config)
        for attempt in range(1, self.smtp_max_retries + 1):
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = self.smtp_username
                msg['To'] = ', '.join(email_config['to'])
                msg['Cc'] = ', '.join(email_config['cc'])
                msg['Subject'] = email_config['subject']
                msg.attach(MIMEText(email_config['body_plain'], 'plain', 'utf-8'))
                msg.attach(MIMEText(email_config['body_html'], 'html', 'utf-8'))
                for filename in email_config.get('attachments', []):
                    if os.path.exists(filename):
                        with open(filename, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}"',
                        )
                        msg.attach(part)
                    else:
                        logger.warning("Attachment not found: %s", filename)
                all_recipients = email_config['to'] + email_config['cc']
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.smtp_use_tls:
                        server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(self.smtp_username, all_recipients, msg.as_string())
                logger.info(
                    "Email sent to %d recipients (attempt %d)",
                    len(all_recipients),
                    attempt,
                )
                return True
            except smtplib.SMTPAuthenticationError as e:
                logger.error("SMTP auth failed (not retrying): %s", e)
                return False
            except Exception as e:
                delay = self.smtp_retry_base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "SMTP attempt %d/%d failed: %s - retry in %.1fs",
                    attempt, self.smtp_max_retries, e, delay,
                )
                time.sleep(delay)
        logger.error("All %d SMTP attempts failed.", self.smtp_max_retries)
        return False

    def _dry_run_preview(self, email_config: Dict) -> bool:
        sep = "=" * 80
        logger.info("\n%s\nDRY RUN MODE - EMAIL PREVIEW\n%s", sep, sep)
        logger.info("TO: %s", ', '.join(email_config['to']))
        logger.info("CC: %s", ', '.join(email_config['cc']))
        logger.info("SUBJECT: %s", email_config['subject'])
        print(email_config['body_plain'][:3000])
        logger.info(
            "Email built | Attachments: %d | Recipients: %d",
            len(email_config.get('attachments', [])),
            len(email_config['to']) + len(email_config['cc']),
        )
        return True

    def send_webhook(self, email_config: Dict) -> bool:
        """POST alert payload to n8n webhook trigger."""
        if not self.n8n_webhook_url:
            logger.warning("N8N_WEBHOOK_URL not set - skipping webhook")
            return False
        payload = json.dumps({
            'source': 'zeus-email-integration-v3',
            'timestamp': datetime.now().isoformat(),
            'protocol_num': email_config.get('protocol_num', ''),
            'severity': email_config.get('severity', ''),
            'subject': email_config.get('subject', ''),
            'recipient_count': (
                len(email_config.get('to', []))
                + len(email_config.get('cc', []))
            ),
            'body_preview': email_config.get('body_plain', '')[:500],
            'attachments': email_config.get('attachments', []),
        }).encode('utf-8')
        req = urllib.request.Request(
            self.n8n_webhook_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("n8n webhook OK (%d)", resp.status)
                return True
        except urllib.error.URLError as e:
            logger.error("n8n webhook failed: %s", e)
            return False

    def get_status_report(self) -> Dict:
        now = datetime.now()
        status: Dict = {
            'timestamp': now.isoformat(),
            'monitored_protocols': len(self.MONITORED_PROTOCOLS),
            'protocols': {},
        }
        for pnum, info in self.MONITORED_PROTOCOLS.items():
            filing = datetime.strptime(info['date'], '%Y-%m-%d')
            if info['deadline_days'] > 0:
                deadline = filing + timedelta(days=info['deadline_days'])
                remaining = (deadline - now).days
                dstatus = 'OVERDUE' if remaining < 0 else 'ACTIVE'
            else:
                remaining = None
                dstatus = 'EXPIRED'
            status['protocols'][pnum] = {
                'name': info['name'],
                'filing_date': info['date'],
                'deadline_days': info['deadline_days'],
                'days_remaining': remaining,
                'deadline_status': dstatus,
                'severity': info['severity'],
            }
        return status


# =====================================================================
# LEGAL NOTIFICATION DISPATCH - DRY RUN
# =====================================================================
if __name__ == "__main__":
    print("=" * 80)
    print(" ZEUS EMAIL INTEGRATION v3.0 - LEGAL FORMAT")
    print(" Kyprianos Estate - Protocol Monitoring System")
    print("=" * 80)

    zeus = ZeusEmailIntegration()

    # Protocol 214142 - AADE Rebuttal (319/320 Smoking Gun)
    alert = {
        'protocol_num': '214142',
        'severity': 'CRITICAL',
    }

    logger.info("Generating legal notification for Protocol 214142...")
    email_config = zeus.process_zeus_alert(alert)

    if email_config is None:
        logger.error("Failed to process protocol alert")
        sys.exit(1)

    zeus.send_email(email_config, dry_run=True)
    print()
    zeus.send_webhook(email_config)

    print("\n" + "=" * 80)
    print(" PROTOCOL STATUS DASHBOARD")
    print("=" * 80)
    report = zeus.get_status_report()
    icons = {'CRITICAL': '\U0001f534', 'HIGH': '\U0001f7e1', 'MEDIUM': '\U0001f7e2'}
    for pnum, info in report['protocols'].items():
        icon = icons.get(info['severity'], '\u26ab')
        days = info['days_remaining']
        if days is None:
            day_str = 'EXPIRED'
        elif days < 0:
            day_str = f'OVERDUE by {abs(days)} days'
        else:
            day_str = f'{days} days remaining'
        print(f" {icon} {pnum:>8s}  {info['name'][:50]}")
        print(f"          {day_str} ({info['deadline_status']})")

    print("\n" + "=" * 80)
    print(" FOR JOHN (IOANNIS) KYPRIANOS")
    print(" Hellenic Navy Veteran | Naturalized U.S. Citizen")
    print(" May 17, 1976 - June 13, 2021")
    print(" His family will not stop until justice is served.")
    print("=" * 80)
