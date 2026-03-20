from django.db import models

class Rule(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    rule_id = models.CharField(max_length=20, unique=True)
    gdpr_article = models.CharField(max_length=20)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)

    def __str__(self):
        return f"{self.rule_id} — {self.gdpr_article}"


class Log(models.Model):
    ACTION_CHOICES = [
        ('READ', 'Read'),
        ('WRITE', 'Write'),
        ('EXPORT', 'Export'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
    ]

    SENSITIVITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('analyst', 'Analyst'),
        ('hr', 'HR'),
        ('intern', 'Intern'),
        ('auditor', 'Auditor'),
    ]

    user_id = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    timestamp = models.DateTimeField()
    resource_accessed = models.CharField(max_length=100)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    sensitivity = models.CharField(max_length=10, choices=SENSITIVITY_CHOICES)
    ip_address = models.CharField(max_length=20)
    declared_purpose = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.user_id} — {self.action} — {self.timestamp}"


class Violation(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('REVIEWING', 'Reviewing'),
        ('RESOLVED', 'Resolved'),
    ]

    log = models.ForeignKey(Log, on_delete=models.CASCADE, related_name='violations')
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name='violations')
    detected_at = models.DateTimeField(auto_now_add=True)
    is_anomaly = models.BooleanField(default=False)
    risk_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    explanation = models.TextField(blank=True)

    def __str__(self):
        return f"Violation [{self.rule.rule_id}] — {self.log.user_id} — Score: {self.risk_score}"