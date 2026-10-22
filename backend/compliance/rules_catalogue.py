"""The detection policy: one entry per row of Auditra_GDPR_Violation_Mapping.xlsx.

Rules are created by migration 0008 and kept in sync by `python manage.py sync_rules`. The admin can switch a
rule off in the console; the code that detects it lives in compliance/detection/.
"""

RULE_DEFINITIONS = [
    # ---- USB_Events sheet --------------------------------------------------------------------------------------
    ('usb_in_shift', 'USB storage connected during shift', ['32'], 'LOW', 'INDICATOR', 'EVENT',
     'A USB storage device was connected during working hours. Risk indicator only.'),
    ('usb_after_shift', 'USB storage connected outside shift', ['32'], 'HIGH', 'VIOLATION', 'EVENT',
     'A USB storage device was connected outside the employee\'s shift.'),
    ('usb_copy_sensitive', 'Sensitive file copied to USB', ['32', '5(1)(f)'], 'HIGH', 'VIOLATION', 'EVENT',
     'A file from a catalogued personal-data folder was written to removable storage. CRITICAL when the file is '
     'HIGH sensitivity or special-category data.'),
    ('usb_mass_export', 'Bulk export of personal records to USB', ['5', '32'], 'CRITICAL', 'VIOLATION', 'WINDOW',
     'Three or more catalogued files copied to removable storage within 10 minutes, with no declared purpose.'),

    # ---- Articles sheet (endpoint + catalogue) --------------------------------------------------------------
    ('role_scope', 'Access beyond role scope', ['25'], 'HIGH', 'VIOLATION', 'EVENT',
     'The resource is more sensitive than the employee\'s role allows, or its data category is not in the '
     'employee\'s permitted categories.'),
    ('special_category', 'Special category data accessed without authorisation', ['9'], 'CRITICAL', 'VIOLATION',
     'EVENT', 'Health or biometric data opened or exported by an employee not authorised for that category.'),
    ('criminal_data', 'Criminal offence data accessed without authorisation', ['10'], 'CRITICAL', 'VIOLATION',
     'EVENT', 'Criminal-record data opened by an employee not authorised for that category.'),
    ('national_id', 'National ID data processed without safeguards', ['87'], 'HIGH', 'VIOLATION', 'EVENT',
     'Records with national ID numbers (CNIC) viewed or exported by an unauthorised employee.'),
    ('employee_data', 'Employee data processed outside HR', ['88'], 'HIGH', 'VIOLATION', 'EVENT',
     'HR / employee records opened by someone outside the HR department.'),
    ('no_lawful_basis', 'Processing without a lawful basis', ['6'], 'HIGH', 'VIOLATION', 'EVENT',
     'The resource belongs to a processing activity that has no lawful basis recorded.'),
    ('not_in_ropa', 'Processing not in the Records of Processing Activities', ['30'], 'MEDIUM', 'VIOLATION', 'EVENT',
     'A catalogued personal-data resource was accessed but no RoPA entry covers it.'),
    ('consent_withdrawn', 'Processing after consent was withdrawn', ['7'], 'CRITICAL', 'VIOLATION', 'EVENT',
     'The data subject withdrew consent, and their data was accessed afterwards.'),
    ('after_erasure', 'Data accessed after erasure was completed', ['17'], 'HIGH', 'VIOLATION', 'EVENT',
     'An erasure request was marked completed, but the data subject\'s file still exists and was accessed.'),
    ('restricted_subject', 'Restricted data processed', ['18'], 'MEDIUM', 'VIOLATION', 'EVENT',
     'The data subject asked for restriction of processing, and their data was read or changed.'),
    ('objection_ignored', 'Objection to processing not respected', ['21'], 'HIGH', 'VIOLATION', 'EVENT',
     'The data subject objected to processing, and processing continued.'),
    ('after_shift_sensitive', 'Sensitive data accessed outside shift', ['32'], 'HIGH', 'VIOLATION', 'EVENT',
     'HIGH-sensitivity data accessed outside the employee\'s working hours.'),
    ('vendor_scope', 'Processor acting beyond instructions', ['29'], 'HIGH', 'VIOLATION', 'EVENT',
     'A vendor account exported or deleted data, accessed a category outside its agreed scope, or was active '
     'outside its agreed hours.'),
    ('departed_employee', 'Account of a departed employee used', ['32'], 'HIGH', 'VIOLATION', 'EVENT',
     'An account that belongs to an employee marked as having left the organisation was used.'),

    # ---- Other_Actions sheet ----------------------------------------------------------------------------------
    ('remote_logon', 'Remote desktop logon', ['32', '25'], 'MEDIUM', 'INDICATOR', 'EVENT',
     'Logon type 10 (Remote Desktop). Escalated to Art. 29 when the account belongs to a vendor.'),
    ('brute_force', 'Many failed logons, then a success', ['32'], 'HIGH', 'VIOLATION', 'WINDOW',
     'Five or more failed logons for one account within 10 minutes, followed by a successful logon.'),
    ('many_machines', 'Logons to many machines in a day', ['32'], 'HIGH', 'VIOLATION', 'WINDOW',
     'One account logged on to three or more different machines on the same day (possible lateral movement).'),
    ('shared_account', 'Shared or generic account', ['32', '5(2)'], 'MEDIUM', 'VIOLATION', 'WINDOW',
     'One account used on two machines within 15 minutes, so its actions cannot be tied to one person.'),
    ('account_created', 'New user account created', ['32', '25'], 'MEDIUM', 'VIOLATION', 'EVENT',
     'A new user account was created (4720).'),
    ('admin_group_add', 'User added to an administrators group', ['25', '32'], 'HIGH', 'VIOLATION', 'EVENT',
     'An account was added to a privileged group (4732).'),
    ('account_lockout', 'Account locked out', ['32'], 'MEDIUM', 'INDICATOR', 'EVENT',
     'Windows locked an account after repeated failed logons (4740).'),
    ('log_cleared', 'Security log cleared', ['32', '5(2)'], 'CRITICAL', 'VIOLATION', 'EVENT',
     'The Windows Security log was cleared (1102). Accountability evidence was destroyed.'),
    ('audit_policy_changed', 'Audit policy changed', ['32', '5(2)'], 'HIGH', 'VIOLATION', 'EVENT',
     'The Windows audit policy was changed (4719).'),
    ('task_created', 'Scheduled task created', ['32'], 'MEDIUM', 'INDICATOR', 'EVENT',
     'A user created a scheduled task (4698), a common persistence technique.'),
    ('mass_read', 'Mass read in a sensitive folder', ['5', '25', '32'], 'HIGH', 'VIOLATION', 'WINDOW',
     'Twenty or more personal-data files opened by one account within 10 minutes.'),
    ('mass_delete', 'Deletion of sensitive files', ['32', '5(1)(f)'], 'HIGH', 'VIOLATION', 'WINDOW',
     'Three or more personal-data files deleted by one account within 10 minutes. CRITICAL for HIGH data.'),
    ('print_sensitive', 'Sensitive document printed', ['32'], 'LOW', 'INDICATOR', 'EVENT',
     'A catalogued personal-data document was printed.'),
    ('file_sharing_site', 'Personal cloud / file-sharing site', ['32', '5'], 'MEDIUM', 'INDICATOR', 'EVENT',
     'A file-sharing or personal cloud site was visited. A potential violation when the same account opened '
     'personal data in the previous 30 minutes.'),
    ('social_media', 'Social media during work', ['Policy'], 'LOW', 'INDICATOR', 'EVENT',
     'Acceptable-use policy indicator. Not a GDPR violation on its own.'),
    ('retention_exceeded', 'Data kept past its retention period', ['5(1)(e)'], 'MEDIUM', 'VIOLATION', 'EVENT',
     'A file is older than the retention period set for its catalogue entry.'),

    # ---- Articles sheet (workflow records) ------------------------------------------------------------------
    ('dsr_overdue', 'Data-subject request not fulfilled within 30 days', ['15', '16', '17', '18', '21'], 'HIGH',
     'VIOLATION', 'WORKFLOW', 'An access, rectification, erasure, restriction or objection request is past its '
     'deadline.'),
    ('portability_denied', 'Portability request denied without exemption', ['20'], 'MEDIUM', 'VIOLATION',
     'WORKFLOW', 'A portability request was denied and no exemption was documented.'),
    ('breach_not_reported', 'Breach not reported within 72 hours', ['33'], 'CRITICAL', 'VIOLATION', 'WORKFLOW',
     'A breach record has no supervisory-authority notification 72 hours after detection.'),
    ('subjects_not_notified', 'Data subjects not notified of a high-risk breach', ['34'], 'HIGH', 'VIOLATION',
     'WORKFLOW', 'A high-risk breach has no data-subject notification recorded within 72 hours.'),
    ('automated_decision', 'Automated decision without human review', ['22'], 'HIGH', 'VIOLATION', 'WORKFLOW',
     'A business system logged a decision with significant effect and nobody reviewed it within 1 hour.'),
    ('dpo_missing', 'No DPO for high-risk processing', ['37'], 'HIGH', 'VIOLATION', 'WORKFLOW',
     'High-risk processing was observed while the DPO record is missing or incomplete.'),

    # ---- AI -----------------------------------------------------------------------------------------------
    ('ai_anomaly', 'Unusual behaviour for this employee-day', ['32'], 'MEDIUM', 'ANOMALY', 'AI',
     'The AI score for the employee-day crossed 60/100 and no rule explains the activity.'),
]


def sync_rules(Rule):
    created = 0
    for code, title, articles, severity, kind, source, description in RULE_DEFINITIONS:
        _, was_created = Rule.objects.update_or_create(
            code=code,
            defaults={
                'title': title,
                'articles': articles,
                'gdpr_article': ', '.join(
                    a if a == 'Policy' else f'Art. {a}' for a in articles
                ),
                'severity': severity,
                'kind': kind,
                'source': source,
                'description': description,
            },
        )
        created += int(was_created)
    return created
