from django.db import models

# Create your models here.

class School(models.Model):
    building_name = models.CharField(max_length=255)
    building_code = models.CharField(max_length=8)
    slug = models.CharField(max_length=255)
    
    district_name = models.CharField(max_length=255)
    district_code = models.CharField(max_length=8)
    district_slug = models.CharField(max_length=255)
    
    