from django.db import models

# Create your models here.

class OriginAdresses(models.Model):
    address=models.CharField(max_length=512)

class RealEstate(models.Model):
    url = models.URLField(max_length=256)
    title = models.CharField(max_length=128)
    price = models.CharField(max_length=50)
    coordinates = models.CharField(max_length=50)
    specs_dict = models.JSONField()

class RealEstateOriginDistances(models.Model):
    origin = models.ForeignKey(OriginAdresses)
    destination = models.ForeignKey(RealEstate)
    duration = models.TimeField()
