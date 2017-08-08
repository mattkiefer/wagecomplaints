# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from census.models import Zip

# Create your models here.
class Complaint(models.Model):
    case_no           = models.TextField()
    case_type         = models.TextField()
    date_filed        = models.DateField(null=True)
    date_closed       = models.DateField(null=True)
    status            = models.TextField()
    claimant_zip_code = models.TextField(null=True)
    #claimaint_city    = models.TextField(null=True) # city is approx based on geocoding
    claimant_zip_data = models.ForeignKey(Zip,models.SET_NULL,null=True)
    employer_zip      = models.TextField(null=True)
    employer_name     = models.TextField()
    industry          = models.TextField()
    amt_claimed       = models.FloatField(null=True)


class MWOT(Complaint):
    amt_resolved = models.FloatField(null=True)
    claim_type   = models.TextField()


class WC(Complaint):
    union_local = models.TextField()
    union_name  = models.TextField()
    translation = models.TextField()
    wages       = models.FloatField(null=True)
    bonus       = models.FloatField(null=True)
    commission  = models.FloatField(null=True)
    deductions  = models.FloatField(null=True)
    vacation    = models.FloatField(null=True)


class Hearing(models.Model):
    case    = models.ForeignKey(Complaint,models.SET_NULL,null=True)
    case_no = models.TextField()
    date    = models.DateField(null=True)
    alj     = models.TextField()


