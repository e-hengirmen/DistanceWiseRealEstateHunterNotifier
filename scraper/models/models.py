from django.db import models

# Create your models here.

class OriginAdresses(models.Model):
    address=models.CharField(max_length=512)

class RealEstate(models.Model):
    url = models.URLField(max_length=255,unique=True)
    title = models.CharField(max_length=128, null=True)
    price = models.IntegerField()
    coordinates = models.CharField(max_length=50, null=True)
    specs_dict = models.JSONField()

class RealEstateOriginDistances(models.Model):
    origin = models.ForeignKey(OriginAdresses, on_delete=models.CASCADE)
    destination = models.ForeignKey(RealEstate, on_delete=models.CASCADE)
    duration = models.IntegerField()  # in seconds
