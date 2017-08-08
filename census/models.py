# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Zip(models.Model):
    zip_code      = models.TextField()
    
    pct_hisp      = models.IntegerField(null=True)
    pct_blk       = models.IntegerField(null=True)
    pct_white     = models.IntegerField(null=True)

    pct_frn_born  = models.IntegerField(null=True)

    pct_poverty   = models.IntegerField(null=True)

    cnt_workforce = models.IntegerField(null=True) 
