from django.db import models

# Create your models here.

class HepsiEmlakScraperLogs(models.Model):
    duration = models.DurationField()
    realestate_count = models.IntegerField(default=0)
    relation_count = models.IntegerField(default=0)
    
